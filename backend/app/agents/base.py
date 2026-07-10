"""Base Agent: one class, many configs.

An agent is a system prompt + an allowlisted tool subset + a model. `run()`
drives the manual tool-use loop against the Anthropic Messages API, emitting
events (for the WebSocket UI) and JSONL decision-log lines as it goes.
"""
from __future__ import annotations

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
            per = budget.by_agent.get(cfg.name, {})
            return AgentResult(
                run_id=run_id,
                agent=cfg.name,
                output=output,
                error=error,
                input_tokens=per.get("input_tokens", 0),
                output_tokens=per.get("output_tokens", 0),
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        async def finish(res: AgentResult) -> AgentResult:
            await emit(
                {
                    "type": "run_completed",
                    "output": res.output,
                    "error": res.error,
                    "duration_ms": res.duration_ms,
                    "usage": budget.by_agent.get(cfg.name, {}),
                }
            )
            return res

        # Construct the client before announcing the run: a missing API key
        # should surface as a clean error, not a forever-spinning run.
        client = self._client_factory()

        await emit({"type": "run_started", "task": task})

        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": task})
        tool_schemas = self.registry.schemas(cfg.tools)
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
                if block.type == "text" and block.text.strip():
                    final_text_parts.append(block.text)
                    await emit({"type": "agent_text", "text": block.text})
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if response.stop_reason != "tool_use" or not tool_uses:
                return await finish(result("\n\n".join(final_text_parts).strip()))

            messages.append({"role": "assistant", "content": response.content})

            # Execute all requested tools, then return every result in ONE
            # user message (splitting them degrades parallel tool use).
            tool_results = []
            for block in tool_uses:
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
                tool_results.append(entry)
            messages.append({"role": "user", "content": tool_results})

        return await finish(
            result(
                "\n\n".join(final_text_parts).strip() or "(no answer)",
                error="max_turns_exceeded",
            )
        )
