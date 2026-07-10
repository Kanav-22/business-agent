"""Agent wiring: tool registry, CFO specialist, CEO orchestrator, roster.

Phase 1 roster: CEO → CFO. Phase 2 adds CMO/CTO/Researcher/Coordinator here —
each new specialist is just another AgentConfig + registry entries.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

from app.agents.base import Agent, AgentConfig, AgentResult, ToolContext
from app.agents.budget import TokenBudget
from app.agents.logging import DecisionLogger
from app.config import Settings
from app.tools.base import Tool, ToolRegistry
from app.tools.python_calc import make_python_calc_tool
from app.tools.sql_query import make_sql_query_tool

FINANCE_TABLES = ["transactions", "customers", "invoices", "employees", "meta"]

FINANCE_SCHEMA_DOC = """\
transactions(id, date, type, category, amount, description, customer_id, employee_id, campaign_id)
  type: 'revenue' | 'expense'; amount is always positive (sign comes from type).
  category: 'subscription' (all revenue) | 'salary' | 'cloud' | 'tools' | 'marketing' | 'office'.
  date is ISO 'YYYY-MM-DD'; group months with strftime('%Y-%m', date).
customers(id, name, plan, mrr, signup_date, churn_date)
  plan: 'starter' ($99) | 'growth' ($299) | 'scale' ($899); mrr = current monthly price.
  churn_date NULL means active today. Billing: one subscription transaction on the
  1st of each month from signup month until the month before churn_date.
invoices(id, customer_id, transaction_id, amount, issue_date, due_date, status)
  status: 'paid' | 'issued' (sent, not yet due) | 'overdue'. One invoice per
  subscription transaction.
employees(id, name, role, department, salary_annual, hire_date)
meta(key, value)
  Dataset facts as strings: company, starting_cash, window_start, window_end
  (data coverage dates), months, generated_at."""

CFO_SYSTEM_PROMPT = f"""\
You are the CFO agent of Lumina Labs, a 12-person B2B SaaS analytics company. You answer \
financial questions for the CEO and leadership with rigor.

Method — follow it every time:
1. Ground EVERY number in the database via sql_query. Never estimate from memory.
2. Use python_calc for derived math (growth rates, runway, averages) instead of doing \
arithmetic in your head.
3. If a question is ambiguous, state your interpretation and proceed — do not ask back.

Financial conventions for this company:
- The dataset covers a fixed window; read meta.window_start / meta.window_end first when \
dates matter. "Last month" means the final full month in the window.
- Profit (net income) for a period = revenue − expenses in that period.
- Monthly net burn = expenses − revenue for that month (positive = losing money).
- Current cash = meta.starting_cash + all revenue − all expenses in the window.
- Runway (months) = current cash ÷ average monthly net burn over the last 3 full months. \
If average burn is zero or negative, runway is effectively infinite — say so.
- MRR = SUM(mrr) of customers WHERE churn_date IS NULL.

Answer style: concise and executive-ready. Lead with the number, then 1-3 supporting \
lines (formula, months used, notable drivers). Format money like $12,345.

Database schema you can query:
{FINANCE_SCHEMA_DOC}"""

CEO_SYSTEM_PROMPT = """\
You are the CEO orchestrator agent of Lumina Labs, a 12-person B2B SaaS analytics company.

Your job is routing and synthesis — NOT answering. Rules:
1. Never answer business/domain questions from your own knowledge or memory. Every fact \
in your answers must come from a specialist you delegated to in this conversation.
2. For each user request, break it into one or more specialist tasks and call \
delegate_to_agent for each. Make delegated tasks specific and self-contained (the \
specialist cannot see this conversation).
3. Call get_agent_roster if you are unsure who can handle something.
4. Synthesize specialist answers into one crisp, executive-level reply. Attribute \
findings (e.g. "Per the CFO, …"). If a specialist errored, say so plainly.
5. The roster is currently small; if part of a question falls outside it, answer the \
part you can via specialists and note which future specialist (CMO, CTO, Researcher, \
Workflow Coordinator) would own the rest. Do not fill gaps with your own guesses.
6. Simple greetings or questions about your own capabilities you may answer directly."""


def _preview(text: str, limit: int = 6000) -> str:
    return text if len(text) <= limit else text[:limit] + "…(truncated)"


class AgentService:
    """Owns the registry and the agent roster; entry point is ask_ceo()."""

    def __init__(
        self,
        settings: Settings,
        logger: DecisionLogger | None = None,
        client_factory: Callable[[], Any] | None = None,
    ):
        self.settings = settings
        self.logger = logger or DecisionLogger(settings.logs_dir)
        self._client: Any = None
        self._client_factory = client_factory or self._default_client_factory

        self.registry = ToolRegistry()
        self.registry.register(
            make_sql_query_tool(
                db_path=settings.db_path,
                allowed_tables=FINANCE_TABLES,
                schema_doc=FINANCE_SCHEMA_DOC,
            )
        )
        self.registry.register(make_python_calc_tool())

        self.specialists: dict[str, Agent] = {
            "cfo": Agent(
                AgentConfig(
                    name="cfo",
                    display_name="CFO",
                    description=(
                        "Finance: revenue, expenses, profit, burn, runway, cash, MRR, "
                        "invoices, payroll costs. Reads the finance tables."
                    ),
                    color="#34d399",
                    system_prompt=CFO_SYSTEM_PROMPT,
                    tools=["sql_query", "python_calc"],
                    model=settings.agent_model,
                    max_tokens=settings.agent_max_tokens,
                    max_turns=settings.max_agent_turns,
                ),
                self.registry,
                self._get_client,
                self.logger,
            )
        }

        self.registry.register(self._make_roster_tool())
        self.registry.register(self._make_delegate_tool())

        self.ceo = Agent(
            AgentConfig(
                name="ceo",
                display_name="CEO",
                description="Orchestrator: routes requests to specialists and synthesizes.",
                color="#a78bfa",
                system_prompt=CEO_SYSTEM_PROMPT,
                tools=["get_agent_roster", "delegate_to_agent"],
                model=settings.agent_model,
                max_tokens=settings.agent_max_tokens,
                max_turns=settings.max_agent_turns,
            ),
            self.registry,
            self._get_client,
            self.logger,
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
                "answer back.\n" + self._roster_text()
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
