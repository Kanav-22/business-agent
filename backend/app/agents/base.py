"""Base Agent: one class, many configs.

An agent is a system prompt + an allowlisted tool subset + a model. `run()`
drives the manual tool-use loop against the Anthropic Messages API, emitting
events (for the WebSocket UI) and JSONL decision-log lines as it goes.

Phase 2 additions:
- parallel tool execution (all tool_use blocks of a turn run concurrently and
  return in ONE user message — this is what makes CEO fan-out parallel)
- Anthropic server-side tools (web_search / web_fetch) via config.server_tools,
  including 'pause_turn' resumption and event emission for server tool blocks
- per-run token usage (delta against the shared budget)
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.agents.budget import BudgetExceeded, TokenBudget
from app.agents.logging import DecisionLogger
from app.tools.base import ToolRegistry

EventSink = Callable[[dict], Awaitable[None]]

_EVENT_PREVIEW_CHARS = 1500


@dataclass
class AgentConfig:
    name: str  # machine name, e.g. "cfo"
    display_name: str  # e.g. "CFO"
    description: str  # shown in the roster / used by the CEO to route
    color: str  # UI accent, e.g. "#34d399"
    system_prompt: str
    tools: list[str]
    model: str
    # Anthropic server-side tool declarations (raw dicts appended to `tools`
    # in the API request). Executed on Anthropic's side — no handler here.
    server_tools: list[dict] = field(default_factory=list)
    max_tokens: int = 4096
    max_turns: int = 12


@dataclass
class AgentResult:
    run_id: str
    agent: str
    output: str
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


@dataclass
class ToolContext:
    """Handed to every tool handler; lets delegation tools spawn child runs."""

    agent: str
    run_id: str
    depth: int
    budget: TokenBudget
    on_event: EventSink
    extra: dict[str, Any] = field(default_factory=dict)


def _server_result_preview(block: Any) -> tuple[str, bool]:
    """Compact, defensive rendering of a server tool result block."""
    content = getattr(block, "content", None)
    if isinstance(content, list):
        lines = []
        for item in content[:5]:
            title = getattr(item, "title", "") or ""
            url = getattr(item, "url", "") or ""
            line = f"- {title} {url}".strip()
            if line != "-":
                lines.append(line)
        return ("\n".join(lines) or "(no results)", False)
    error_code = getattr(content, "error_code", None)
    if error_code:
        return (f"error: {error_code}", True)
    url = getattr(content, "url", None)
    if url:
        return (f"fetched {url}", False)
    return (str(content)[:300], False)


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        registry: ToolRegistry,
        client_factory: Callable[[], Any],
        logger: DecisionLogger,
    ):
        self.config = config
        self.registry = registry
        self._client_factory = client_factory
        self.logger = logger

    async def run(
        self,
        task: str,
        *,
        on_event: EventSink,
        budget: TokenBudget,
        depth: int = 0,
        parent_run_id: str | None = None,
        history: list[dict] | None = None,
    ) -> AgentResult:
        cfg = self.config
        run_id = uuid.uuid4().hex[:12]
        started = time.monotonic()
        usage_at_start = dict(budget.by_agent.get(cfg.name, {}))

        def run_usage() -> dict:
            per = budget.by_agent.get(cfg.name, {})
            return {
                "input_tokens": per.get("input_tokens", 0)
                - usage_at_start.get("input_tokens", 0),
                "output_tokens": per.get("output_tokens", 0)
                - usage_at_start.get("output_tokens", 0),
            }

        async def emit(event: dict) -> None:
            event = {
                "ts": time.time(),
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "agent": cfg.name,
                "agent_display": cfg.display_name,
                "color": cfg.color,
                "depth": depth,
                **event,
            }
            self.logger.log(event)
            await on_event(event)

        def result(output: str, error: str | None = None) -> AgentResult:
            usage = run_usage()
            return AgentResult(
                run_id=run_id,
                agent=cfg.name,
                output=output,
                error=error,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        async def finish(res: AgentResult) -> AgentResult:
            await emit(
                {
                    "type": "run_completed",
                    "output": res.output,
                    "error": res.error,
                    "duration_ms": res.duration_ms,
                    "usage": run_usage(),
                }
            )
            return res

        # Construct the client before announcing the run: a missing API key
        # should surface as a clean error, not a forever-spinning run.
        client = self._client_factory()

        await emit({"type": "run_started", "task": task})

        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": task})
        tool_schemas = self.registry.schemas(cfg.tools) + list(cfg.server_tools)
        ctx = ToolContext(
            agent=cfg.name, run_id=run_id, depth=depth, budget=budget, on_event=on_event
        )

        final_text_parts: list[str] = []
        for _turn in range(cfg.max_turns):
            try:
                budget.check_remaining()
                response = await client.messages.create(
                    model=cfg.model,
                    max_tokens=cfg.max_tokens,
                    system=cfg.system_prompt,
                    tools=tool_schemas,
                    messages=messages,
                )
            except BudgetExceeded as exc:
                return await finish(result(str(exc), error="budget_exceeded"))
            except Exception as exc:
                msg = f"Model call failed: {type(exc).__name__}: {exc}"
                return await finish(result(msg, error="model_error"))

            try:
                budget.add(cfg.name, response.usage)
            except BudgetExceeded as exc:
                return await finish(result(str(exc), error="budget_exceeded"))

            tool_uses = []
            for block in response.content:
                btype = getattr(block, "type", "")
                if btype == "text" and block.text.strip():
                    final_text_parts.append(block.text)
                    await emit({"type": "agent_text", "text": block.text})
                elif btype == "tool_use":
                    tool_uses.append(block)
                elif btype == "server_tool_use":
                    await emit(
                        {
                            "type": "tool_call",
                            "tool": block.name,
                            "tool_use_id": block.id,
                            "input": block.input,
                            "server": True,
                        }
                    )
                elif btype.endswith("_tool_result"):
                    output, is_error = _server_result_preview(block)
                    await emit(
                        {
                            "type": "tool_result",
                            "tool": btype.removesuffix("_tool_result"),
                            "tool_use_id": getattr(block, "tool_use_id", None),
                            "is_error": is_error,
                            "output": output,
                            "server": True,
                        }
                    )

            # Server-side tool loop hit its iteration limit — resume as-is.
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            if response.stop_reason != "tool_use" or not tool_uses:
                return await finish(result("\n\n".join(final_text_parts).strip()))

            messages.append({"role": "assistant", "content": response.content})

            # Execute all requested tools CONCURRENTLY, then return every
            # result in ONE user message (order preserved; splitting results
            # across messages degrades the model's parallel tool use).
            async def execute_one(block) -> dict:
                await emit(
                    {
                        "type": "tool_call",
                        "tool": block.name,
                        "tool_use_id": block.id,
                        "input": block.input,
                    }
                )
                output, is_error = await self.registry.execute(block.name, block.input, ctx)
                await emit(
                    {
                        "type": "tool_result",
                        "tool": block.name,
                        "tool_use_id": block.id,
                        "is_error": is_error,
                        "output": output[:_EVENT_PREVIEW_CHARS]
                        + ("…" if len(output) > _EVENT_PREVIEW_CHARS else ""),
                    }
                )
                entry: dict = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                }
                if is_error:
                    entry["is_error"] = True
                return entry

            tool_results = list(await asyncio.gather(*(execute_one(b) for b in tool_uses)))
            messages.append({"role": "user", "content": tool_results})

        return await finish(
            result(
                "\n\n".join(final_text_parts).strip() or "(no answer)",
                error="max_turns_exceeded",
            )
        )
