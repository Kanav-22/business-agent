"""Agent wiring: per-agent tool registries, the C-suite roster, CEO orchestrator.

Phase 2 roster: CEO → CFO / CMO / CTO / Researcher / Workflow Coordinator.
Each specialist gets ONLY the tools (and only the table docs) it needs.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

from app.agents.base import Agent, AgentConfig, AgentResult, ToolContext
from app.agents.budget import TokenBudget
from app.agents.logging import DecisionLogger
from app.agents.schema_docs import (
    ENGINEERING_TABLES,
    FINANCE_TABLES,
    MARKETING_TABLES,
    WORKFLOW_TABLES,
    build_schema_doc,
)
from app.config import Settings
from app.db import make_engine
from app.tools.base import Tool, ToolRegistry
from app.tools.create_task import make_create_task_tool
from app.tools.python_calc import make_python_calc_tool
from app.tools.sql_query import make_sql_query_tool

# Kept as a public alias — used by tests and by the finance schema docs.
FINANCE_SCHEMA_DOC = build_schema_doc(FINANCE_TABLES)

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
WEB_FETCH_TOOL = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5}

_COMPANY_CONTEXT = (
    "Lumina Labs, a 12-person B2B SaaS analytics company (plans: starter $99, "
    "growth $299, scale $899 per month)."
)

_GROUNDING_RULES = """\
Method — follow it every time:
1. Ground EVERY number in the database via sql_query. Never estimate from memory.
2. If a question is ambiguous, state your interpretation and proceed — do not ask back.
3. The dataset covers a fixed window; read meta.window_start / meta.window_end when \
dates matter. "Last month" means the final full month in the window.

Answer style: concise and executive-ready. Lead with the answer, then 1-3 supporting \
lines. Format money like $12,345."""

CFO_SYSTEM_PROMPT = f"""\
You are the CFO agent of {_COMPANY_CONTEXT} You answer financial questions for the CEO \
and leadership with rigor.

{_GROUNDING_RULES}

Use python_calc for derived math (growth rates, runway, averages) instead of doing \
arithmetic in your head.

Financial conventions for this company:
- Profit (net income) for a period = revenue − expenses in that period.
- Monthly net burn = expenses − revenue for that month (positive = losing money).
- Current cash = meta.starting_cash + all revenue − all expenses in the window.
- Runway (months) = current cash ÷ average monthly net burn over the last 3 full months. \
If average burn is zero or negative, runway is effectively infinite — say so.
- MRR = SUM(mrr) of customers WHERE churn_date IS NULL.

Database schema you can query:
{build_schema_doc(FINANCE_TABLES)}"""

CMO_SYSTEM_PROMPT = f"""\
You are the CMO agent of {_COMPANY_CONTEXT} You answer marketing questions: campaign \
performance, channels, acquisition, CAC, lead quality.

{_GROUNDING_RULES}

Marketing conventions:
- CAC for a channel/campaign = spend ÷ conversions (guard against zero conversions).
- New customers per month come from customers.signup_date; campaign conversions cover \
55-80% of signups (the rest is organic) — say so when comparing.
- You may use web_search for OUTSIDE information only (benchmarks, market context), \
never for internal numbers. Cite URLs when you use it.

Database schema you can query:
{build_schema_doc(MARKETING_TABLES)}"""

CTO_SYSTEM_PROMPT = f"""\
You are the CTO agent of {_COMPANY_CONTEXT} You answer engineering questions: project \
status, deadlines, risk, team capacity and blockers.

{_GROUNDING_RULES}

Engineering conventions:
- A project is on track if status is 'active' or 'completed' and its deadline is not \
past; 'at_risk' projects deserve a one-line explanation from their description.
- Blocked engineering work lives in tasks (status = 'blocked', blocked_reason says why).
- Capacity questions: count Engineering/Product employees and their roles.

Database schema you can query:
{build_schema_doc(ENGINEERING_TABLES)}"""

RESEARCHER_SYSTEM_PROMPT = f"""\
You are the Researcher agent of {_COMPANY_CONTEXT} You answer questions about the \
outside world: competitors, market trends, pricing landscapes, technology choices.

Method:
1. You have NO access to internal company data — that is the other specialists' job. \
Use web_search (and web_fetch for specific pages) for everything.
2. Prefer recent, primary sources. ALWAYS cite the URLs you relied on.
3. Be explicit about uncertainty and about when sources disagree.

Answer style: a short synthesis first, then bullet points with citations."""

COORDINATOR_SYSTEM_PROMPT = f"""\
You are the Workflow Coordinator agent of {_COMPANY_CONTEXT} You manage the \
cross-department task list: what's open, in progress, blocked and overdue — and you \
create new tasks when asked.

{_GROUNDING_RULES}

Coordination conventions:
- "Blocked this week" = tasks with status 'blocked'; always include blocked_reason.
- Overdue = due_date before the data window end and status != 'done'.
- Use create_task to add tasks (it validates input; new tasks cannot be 'done'). \
Only create tasks that were explicitly requested.

Database schema you can query:
{build_schema_doc(WORKFLOW_TABLES)}"""

CEO_SYSTEM_PROMPT = """\
You are the CEO orchestrator agent of Lumina Labs, a 12-person B2B SaaS analytics company.

Your job is routing and synthesis — NOT answering. Rules:
1. Never answer business/domain questions from your own knowledge or memory. Every fact \
in your answers must come from a specialist you delegated to in this conversation.
2. For each user request, break it into one or more specialist tasks and call \
delegate_to_agent for each. Make delegated tasks specific and self-contained (the \
specialist cannot see this conversation).
3. DELEGATE IN PARALLEL: when a request spans several specialists, emit ALL the \
delegate_to_agent calls in a single response — they run concurrently. A broad question \
like "how is the business doing?" should fan out to cfo, cmo and cto (and coordinator \
for blockers) at once.
4. Call get_agent_roster if you are unsure who can handle something.
5. Synthesize specialist answers into one crisp, executive-level brief. ATTRIBUTE every \
finding to its source agent (e.g. "Per the CFO, …"; "The CMO reports …"). If a \
specialist errored, say so plainly.
6. If part of a question falls outside the roster, answer the parts you can via \
specialists and say plainly what you cannot cover. Do not fill gaps with your own \
guesses.
7. Simple greetings or questions about your own capabilities you may answer directly."""


def _preview(text: str, limit: int = 6000) -> str:
    return text if len(text) <= limit else text[:limit] + "…(truncated)"


def _registry(*tools: Tool) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


class AgentService:
    """Owns the roster; entry point is ask_ceo()."""

    def __init__(
        self,
        settings: Settings,
        logger: DecisionLogger | None = None,
        client_factory: Callable[[], Any] | None = None,
    ):
        self.settings = settings
        self.logger = logger or DecisionLogger(settings.logs_dir)
        self.engine = make_engine(settings.db_path)
        self._client: Any = None
        self._client_factory = client_factory or self._default_client_factory

        def sql_tool(tables: list[str]) -> Tool:
            return make_sql_query_tool(
                db_path=settings.db_path,
                allowed_tables=tables,
                schema_doc=build_schema_doc(tables),
            )

        def agent(
            name: str,
            display_name: str,
            description: str,
            color: str,
            system_prompt: str,
            registry: ToolRegistry,
            tools: list[str],
            server_tools: list[dict] | None = None,
        ) -> Agent:
            return Agent(
                AgentConfig(
                    name=name,
                    display_name=display_name,
                    description=description,
                    color=color,
                    system_prompt=system_prompt,
                    tools=tools,
                    server_tools=server_tools or [],
                    model=settings.agent_model,
                    max_tokens=settings.agent_max_tokens,
                    max_turns=settings.max_agent_turns,
                ),
                registry,
                self._get_client,
                self.logger,
            )

        self.specialists: dict[str, Agent] = {
            "cfo": agent(
                "cfo",
                "CFO",
                "Finance: revenue, expenses, profit, burn, runway, cash, MRR, "
                "invoices, payroll costs.",
                "#34d399",
                CFO_SYSTEM_PROMPT,
                _registry(sql_tool(FINANCE_TABLES), make_python_calc_tool()),
                ["sql_query", "python_calc"],
            ),
            "cmo": agent(
                "cmo",
                "CMO",
                "Marketing: campaign performance, channels, CAC, leads, "
                "conversions, acquisition trends; external market benchmarks.",
                "#f472b6",
                CMO_SYSTEM_PROMPT,
                _registry(sql_tool(MARKETING_TABLES)),
                ["sql_query"],
                server_tools=[WEB_SEARCH_TOOL],
            ),
            "cto": agent(
                "cto",
                "CTO",
                "Engineering: project status, deadlines, at-risk work, blocked "
                "engineering tasks, team capacity.",
                "#38bdf8",
                CTO_SYSTEM_PROMPT,
                _registry(sql_tool(ENGINEERING_TABLES)),
                ["sql_query"],
            ),
            "researcher": agent(
                "researcher",
                "Researcher",
                "External research: competitors, market trends, pricing "
                "landscapes, technology evaluations. Web only — no internal data.",
                "#fbbf24",
                RESEARCHER_SYSTEM_PROMPT,
                _registry(),
                [],
                server_tools=[WEB_SEARCH_TOOL, WEB_FETCH_TOOL],
            ),
            "coordinator": agent(
                "coordinator",
                "Coordinator",
                "Workflow: the cross-department task list — open/blocked/overdue "
                "work — and creating new tasks.",
                "#94a3b8",
                COORDINATOR_SYSTEM_PROMPT,
                _registry(sql_tool(WORKFLOW_TABLES), make_create_task_tool(self.engine)),
                ["sql_query", "create_task"],
            ),
        }

        self.ceo = agent(
            "ceo",
            "CEO",
            "Orchestrator: routes requests to specialists (in parallel) and synthesizes.",
            "#a78bfa",
            CEO_SYSTEM_PROMPT,
            _registry(self._make_roster_tool(), self._make_delegate_tool()),
            ["get_agent_roster", "delegate_to_agent"],
        )

    # ------------------------------------------------------------------ client

    def _default_client_factory(self):
        import anthropic

        return anthropic.AsyncAnthropic()

    def _get_client(self):
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    # ------------------------------------------------------------------- tools

    def _roster_text(self) -> str:
        lines = [
            f"- {a.config.name}: {a.config.display_name} — {a.config.description}"
            for a in self.specialists.values()
        ]
        return "Available specialist agents:\n" + "\n".join(lines)

    def _make_roster_tool(self) -> Tool:
        async def handler(tool_input: dict, ctx: ToolContext) -> str:
            return self._roster_text()

        return Tool(
            name="get_agent_roster",
            description="List the specialist agents you can delegate to, with their expertise.",
            input_schema={"type": "object", "properties": {}},
            handler=handler,
        )

    def _make_delegate_tool(self) -> Tool:
        service = self

        async def handler(tool_input: dict, ctx: ToolContext) -> str:
            name = (tool_input.get("agent") or "").strip().lower()
            task = (tool_input.get("task") or "").strip()
            if not task:
                return "Delegation failed: empty task."
            agent = service.specialists.get(name)
            if agent is None:
                return f"Delegation failed: no agent named {name!r}. {service._roster_text()}"
            if ctx.depth + 1 > service.settings.max_delegation_depth:
                return (
                    "Delegation refused: maximum delegation depth "
                    f"({service.settings.max_delegation_depth}) reached."
                )
            result = await agent.run(
                task,
                on_event=ctx.on_event,
                budget=ctx.budget,
                depth=ctx.depth + 1,
                parent_run_id=ctx.run_id,
            )
            if result.error:
                return (
                    f"[{agent.config.display_name} FAILED: {result.error}] "
                    f"{_preview(result.output)}"
                )
            return f"[{agent.config.display_name} answered]\n{_preview(result.output)}"

        agent_names = sorted(self.specialists.keys())
        return Tool(
            name="delegate_to_agent",
            description=(
                "Delegate a self-contained task to a specialist agent and get their "
                "answer back. To parallelize, emit several delegate_to_agent calls "
                "in one response.\n" + self._roster_text()
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": agent_names,
                        "description": "Which specialist to delegate to.",
                    },
                    "task": {
                        "type": "string",
                        "description": (
                            "The task, fully self-contained: include timeframes, "
                            "definitions and any context the specialist needs."
                        ),
                    },
                },
                "required": ["agent", "task"],
            },
            handler=handler,
        )

    # ------------------------------------------------------------------- entry

    async def ask_ceo(
        self,
        message: str,
        *,
        on_event,
        history: list[dict] | None = None,
    ) -> tuple[AgentResult, TokenBudget]:
        budget = TokenBudget(limit=self.settings.token_budget)
        self.logger.log(
            {
                "type": "chat_request",
                "message": message,
                "date": dt.date.today().isoformat(),
            }
        )
        result = await self.ceo.run(
            message, on_event=on_event, budget=budget, history=history
        )
        return result, budget
