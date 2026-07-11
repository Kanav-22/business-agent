"""Agent wiring: per-agent tool registries, the C-suite roster, CEO orchestrator.

Phase 3 org chart:

    CEO ──► CFO ──► FP&A / Reporting / Revenue / Control   (finance sub-team)
        ──► CMO / CTO / Researcher / Workflow Coordinator

The CFO mirrors the CEO pattern one level down: it routes finance questions to
its sub-team and synthesizes. Each agent gets ONLY the tools (and only the
table docs) it needs.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

from app.agents.base import Agent, AgentConfig, AgentResult, ToolContext
from app.agents.budget import TokenBudget
from app.agents.logging import DecisionLogger
from app.agents.survival import apply_survival
from app.agents.schema_docs import (
    CONTROL_TABLES,
    ENGINEERING_TABLES,
    FINANCE_TABLES,
    MARKETING_TABLES,
    REVENUE_TABLES,
    WORKFLOW_TABLES,
    build_schema_doc,
)
from app.config import Settings
from app.db import make_engine
from app.tools.base import Tool, ToolRegistry
from app.tools.content_writer import make_content_writer_tool
from app.tools.create_task import make_create_task_tool
from app.tools.python_calc import make_python_calc_tool
from app.tools.report_writer import make_report_writer_tool
from app.tools.save_memory import make_save_memory_tool
from app.tools.score_idea import make_score_idea_tool
from app.tools.sql_query import make_sql_query_tool
from app.venture.agents import (
    COO_SYSTEM_PROMPT,
    INTERVIEWER_SYSTEM_PROMPT,
    RED_TEAM_SYSTEM_PROMPT,
    RISK_SYSTEM_PROMPT,
    SALES_SYSTEM_PROMPT,
    SCORER_SYSTEM_PROMPT,
    VENTURE_CEO_SYSTEM_PROMPT,
    VENTURE_CFO_SYSTEM_PROMPT,
    VENTURE_CMO_SYSTEM_PROMPT,
    VENTURE_CTO_SYSTEM_PROMPT,
)

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

_FINANCE_CONVENTIONS = """\
Financial conventions for this company:
- Profit (net income) for a period = revenue − expenses in that period.
- Monthly net burn = expenses − revenue for that month (positive = losing money).
- Current cash = meta.starting_cash + all revenue − all expenses in the window.
- Runway (months) = current cash ÷ average monthly net burn over the last 3 full months. \
If average burn is zero or negative, runway is effectively infinite — say so.
- MRR = SUM(mrr) of customers WHERE churn_date IS NULL."""

FPA_SYSTEM_PROMPT = f"""\
You are the FP&A agent of {_COMPANY_CONTEXT} You handle financial planning & analysis: \
profit, burn, runway, cash, budget-vs-actual and forecasts.

{_GROUNDING_RULES}

Use python_calc for derived math (growth rates, runway, forecasts) instead of doing \
arithmetic in your head. For forecasts, use simple explicit models (e.g. average of \
recent MoM growth applied forward) and STATE your assumptions.

{_FINANCE_CONVENTIONS}

Database schema you can query:
{build_schema_doc(FINANCE_TABLES)}"""

REPORTING_SYSTEM_PROMPT = f"""\
You are the Reporting agent of {_COMPANY_CONTEXT} You produce formal finance documents \
(P&L statements, expense breakdowns, monthly summaries).

{_GROUNDING_RULES}

Your workflow, always in this order:
1. Gather and verify every number with sql_query.
2. Save the document with report_writer (title + ordered sections; use markdown \
tables for figures).
3. Reply with a one-paragraph summary and the saved report id.

{_FINANCE_CONVENTIONS}

Database schema you can query:
{build_schema_doc(FINANCE_TABLES)}"""

REVENUE_SYSTEM_PROMPT = f"""\
You are the Revenue agent of {_COMPANY_CONTEXT} You handle accounts receivable and \
revenue quality: invoices (issued/paid/overdue), MRR movements, churn and expansion.

{_GROUNDING_RULES}

Revenue conventions:
- AR outstanding = invoices with status 'issued' or 'overdue'.
- MRR movement between months: new (signups), expansion (price increases), churned \
(churn_date set). Customers are billed on the 1st; churn_date month is unbilled.

Database schema you can query:
{build_schema_doc(REVENUE_TABLES)}"""

CONTROL_SYSTEM_PROMPT = f"""\
You are the Control agent of {_COMPANY_CONTEXT} You run reconciliation and anomaly \
checks — you are the skeptic of the finance team.

{_GROUNDING_RULES}

Your standard checks (run the relevant ones, or all when asked for a full check):
1. Billing reconciliation: for the last full month, subscription revenue must equal \
the sum of amounts billed to customers active that month, with one transaction per \
customer.
2. Payroll reconciliation: monthly salary spend must equal the sum of salary_annual/12 \
of employees hired by that month.
3. Marketing reconciliation: per campaign, marketing transactions must sum to \
campaigns.spend.
4. Invoices: one invoice per subscription transaction, equal amounts; report the \
overdue count and value.
5. Anomalies: any expense category moving more than ±30% month-over-month; any \
duplicate transactions.

Report each check as a line: [OK] / [WARN] / [CRITICAL] with the numbers that prove it. \
Use python_calc for arithmetic.

Database schema you can query:
{build_schema_doc(CONTROL_TABLES)}"""

CFO_SYSTEM_PROMPT = """\
You are the CFO agent of Lumina Labs, a 12-person B2B SaaS analytics company. You lead \
the finance team; your job is routing finance work to your sub-team and synthesizing \
their answers — NOT answering from memory.

Rules:
1. Every number in your answers must come from a sub-team agent you delegated to.
2. Make delegated tasks specific and self-contained. Delegate to several sub-agents \
IN PARALLEL (all delegate_to_agent calls in one response) when a request spans areas.
3. Route: profit/burn/runway/cash/forecasts/budget → fpa. Formal documents ("produce a \
P&L report") → reporting. Invoices/AR/MRR movements/churn revenue → revenue. \
Reconciliation, "does X add up", unusual/anomalous spend → control.
4. Synthesize into one crisp answer and attribute ("Per FP&A…", "Control flags…"). \
If a sub-agent errored, say so plainly.

Your sub-team (use these exact names with delegate_to_agent):
- fpa — planning & analysis: profit, burn, runway, cash, forecasts
- reporting — formal finance reports, saved to the reports library
- revenue — invoices, AR, MRR movements, churn/expansion
- control — reconciliation and anomaly checks"""

CONTENT_SYSTEM_PROMPT = f"""\
You are the Content agent of {_COMPANY_CONTEXT} You draft marketing content: blog \
posts, emails, social posts, launch announcements.

Method:
1. You have NO database access. Work strictly from the brief you were given — use the \
facts and numbers in it verbatim; never invent metrics. You may use web_search for \
outside context or inspiration.
2. Write the COMPLETE draft, then submit it with content_writer. That places it in \
the human Approvals inbox — nothing you write is published without human sign-off, \
so always finish by submitting.
3. Voice: clear, concrete, benefit-led. No hype clichés ("game-changing", \
"revolutionize"), no exclamation-mark pileups.

Reply after submitting with the draft id and a one-line summary."""

CMO_SYSTEM_PROMPT = f"""\
You are the CMO agent of {_COMPANY_CONTEXT} You answer marketing questions — campaign \
performance, channels, acquisition, CAC, lead quality — and you commission marketing \
content.

{_GROUNDING_RULES}

Marketing conventions:
- CAC for a channel/campaign = spend ÷ conversions (guard against zero conversions).
- New customers per month come from customers.signup_date; campaign conversions cover \
55-80% of signups (the rest is organic) — say so when comparing.
- You may use web_search for OUTSIDE information only (benchmarks, market context), \
never for internal numbers. Cite URLs when you use it.

Your sub-team: content — drafts posts/emails/announcements and submits them to the \
human Approvals inbox (nothing is published without a click). When asked to draft or \
propose content, first gather any numbers yourself with sql_query, then \
delegate_to_agent('content') with a complete, self-contained brief that includes \
those facts, the channel, audience and goal. Tell the requester the draft is waiting \
in Approvals.

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
4. The cfo leads a finance sub-team (FP&A, Reporting, Revenue, Control) and the cmo \
leads a content sub-team — both route internally. Send finance questions to the cfo \
and marketing/content-drafting requests to the cmo, not to sub-team members. Content \
drafts always land in the human Approvals inbox, never publish directly — say so \
when relevant.
5. Call get_agent_roster if you are unsure who can handle something.
6. Synthesize specialist answers into one crisp, executive-level brief. ATTRIBUTE every \
finding to its source agent (e.g. "Per the CFO, …"; "The CMO reports …"). If a \
specialist errored, say so plainly.
7. If part of a question falls outside the roster, answer the parts you can via \
specialists and say plainly what you cannot cover. Do not fill gaps with your own \
guesses.
8. Simple greetings or questions about your own capabilities you may answer directly."""


def _preview(text: str, limit: int = 6000) -> str:
    return text if len(text) <= limit else text[:limit] + "…(truncated)"


def _registry(*tools: Tool) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


def _roster_text(roster: dict[str, Agent]) -> str:
    lines = [
        f"- {a.config.name}: {a.config.display_name} — {a.config.description}"
        for a in roster.values()
    ]
    return "Available specialist agents:\n" + "\n".join(lines)


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
                    # SURVIVAL_MODE=1 appends the guide scaffolding from
                    # docs/survival/; default off leaves prompts byte-identical.
                    system_prompt=apply_survival(
                        name, system_prompt, enabled=settings.survival_mode
                    ),
                    tools=tools,
                    # Server-side web tools are Anthropic-only; strip them when
                    # running behind a non-Anthropic proxy (WEB_TOOLS_ENABLED=0).
                    server_tools=(server_tools or []) if settings.web_tools_enabled else [],
                    model=settings.agent_model,
                    max_tokens=settings.agent_max_tokens,
                    max_turns=settings.max_agent_turns,
                ),
                registry,
                self._get_client,
                self.logger,
            )

        # ------------------------------------------------- finance sub-team
        self.finance_team: dict[str, Agent] = {
            "fpa": agent(
                "fpa",
                "FP&A",
                "Planning & analysis: profit, burn, runway, cash, budget vs "
                "actual, forecasts.",
                "#2dd4bf",
                FPA_SYSTEM_PROMPT,
                _registry(sql_tool(FINANCE_TABLES), make_python_calc_tool()),
                ["sql_query", "python_calc"],
            ),
            "reporting": agent(
                "reporting",
                "Reporting",
                "Formal finance documents (P&L, expense breakdowns), saved to "
                "the reports library.",
                "#a3e635",
                REPORTING_SYSTEM_PROMPT,
                _registry(sql_tool(FINANCE_TABLES), make_report_writer_tool(self.engine)),
                ["sql_query", "report_writer"],
            ),
            "revenue": agent(
                "revenue",
                "Revenue",
                "Accounts receivable, invoices (issued/paid/overdue), MRR "
                "movements, churn and expansion.",
                "#4ade80",
                REVENUE_SYSTEM_PROMPT,
                _registry(sql_tool(REVENUE_TABLES)),
                ["sql_query"],
            ),
            "control": agent(
                "control",
                "Control",
                "Reconciliation and anomaly checks: does the data add up, what "
                "moved unexpectedly.",
                "#fb7185",
                CONTROL_SYSTEM_PROMPT,
                _registry(sql_tool(CONTROL_TABLES), make_python_calc_tool()),
                ["sql_query", "python_calc"],
            ),
        }

        # ---------------------------------------------------- content sub-team
        self.content_team: dict[str, Agent] = {
            "content": agent(
                "content",
                "Content",
                "Drafts marketing content (blog posts, emails, social, "
                "announcements); every draft goes to the human Approvals inbox.",
                "#e879f9",
                CONTENT_SYSTEM_PROMPT,
                _registry(make_content_writer_tool(self.engine)),
                ["content_writer"],
                server_tools=[WEB_SEARCH_TOOL],
            ),
        }

        # ------------------------------------------------------- specialists
        self.specialists: dict[str, Agent] = {
            "cfo": agent(
                "cfo",
                "CFO",
                "Finance: revenue, expenses, profit, burn, runway, cash, MRR, "
                "invoices, payroll, reports, reconciliation. Leads the finance "
                "sub-team (FP&A, Reporting, Revenue, Control).",
                "#34d399",
                CFO_SYSTEM_PROMPT,
                _registry(self._make_delegate_tool(self.finance_team)),
                ["delegate_to_agent"],
            ),
            "cmo": agent(
                "cmo",
                "CMO",
                "Marketing: campaign performance, channels, CAC, leads, "
                "conversions, acquisition trends, market benchmarks; commissions "
                "content drafts (via its Content sub-agent → Approvals inbox).",
                "#f472b6",
                CMO_SYSTEM_PROMPT,
                _registry(
                    sql_tool(MARKETING_TABLES),
                    self._make_delegate_tool(self.content_team),
                ),
                ["sql_query", "delegate_to_agent"],
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

        # ------------------------------------------------------- venture team
        # Founder-facing agents (validating/launching NEW businesses). They are
        # driven by the venture workflows (app/venture/workflows.py) and join
        # the CEO's chat roster only when VENTURE_IN_CHAT=1.
        self.venture_team: dict[str, Agent] = {
            "venture_ceo": agent(
                "venture_ceo",
                "CEO (Venture)",
                "Venture strategy: proposes plans for new businesses, revises "
                "them after board objections, makes the final call.",
                "#c084fc",
                VENTURE_CEO_SYSTEM_PROMPT,
                _registry(),
                [],
            ),
            "venture_cfo": agent(
                "venture_cfo",
                "CFO (Venture)",
                "Financial skeptic: attacks cost, revenue and runway assumptions "
                "in venture proposals.",
                "#10b981",
                VENTURE_CFO_SYSTEM_PROMPT,
                _registry(make_save_memory_tool(self.engine, ["financial_assumption"])),
                ["save_memory"],
            ),
            "venture_cmo": agent(
                "venture_cmo",
                "CMO (Venture)",
                "Demand skeptic: attacks market-demand and positioning "
                "assumptions in venture proposals.",
                "#f9a8d4",
                VENTURE_CMO_SYSTEM_PROMPT,
                _registry(make_save_memory_tool(self.engine, ["marketing_experiment"])),
                ["save_memory"],
            ),
            "venture_cto": agent(
                "venture_cto",
                "CTO (Venture)",
                "Feasibility skeptic: attacks technical assumptions; scopes the "
                "minimal build that still delivers the promise.",
                "#7dd3fc",
                VENTURE_CTO_SYSTEM_PROMPT,
                _registry(make_save_memory_tool(self.engine, ["product_roadmap"])),
                ["save_memory"],
            ),
            "coo": agent(
                "coo",
                "COO",
                "Execution planning: turns decisions into sequenced plans with "
                "owners, deadlines, checkpoints and kill criteria; attacks "
                "execution complexity in debates.",
                "#fdba74",
                COO_SYSTEM_PROMPT,
                _registry(make_save_memory_tool(self.engine, ["lesson_learned"])),
                ["save_memory"],
            ),
            "risk": agent(
                "risk",
                "Risk Officer",
                "Legal, regulatory, compliance and reputational risk triage: "
                "ranked risks with mitigations and a proceed/don't verdict.",
                "#f87171",
                RISK_SYSTEM_PROMPT,
                _registry(make_save_memory_tool(self.engine, ["risk"])),
                ["save_memory"],
            ),
            "red_team": agent(
                "red_team",
                "Red Team",
                "Attacks ideas, strategies and plans: weakest assumptions, "
                "failure scenarios, severity, fixes. Direct and critical.",
                "#ef4444",
                RED_TEAM_SYSTEM_PROMPT,
                _registry(),
                [],
            ),
            "sales": agent(
                "sales",
                "Sales",
                "Sales copy and strategy that converts a specific persona: "
                "outreach, landing pages, offers, objection handling.",
                "#facc15",
                SALES_SYSTEM_PROMPT,
                _registry(make_save_memory_tool(self.engine, ["sales_conversation"])),
                ["save_memory"],
            ),
            "interviewer": agent(
                "interviewer",
                "Interviewer",
                "Synthetic customer interviews: simulated personas + synthesis "
                "for cheap validation BEFORE talking to real customers.",
                "#a3a3a3",
                INTERVIEWER_SYSTEM_PROMPT,
                _registry(),
                [],
            ),
            "scorer": agent(
                "scorer",
                "Idea Scorer",
                "Strict 1-10 scoring of business ideas across 14 categories; "
                "the Go/No-Go/Test-First verdict is computed deterministically.",
                "#22d3ee",
                SCORER_SYSTEM_PROMPT,
                _registry(make_score_idea_tool(self.engine)),
                ["score_idea"],
            ),
        }

        # The CEO's chat roster: unchanged by default; VENTURE_IN_CHAT=1 lets
        # chat also delegate to the venture team.
        ceo_roster: dict[str, Agent] = dict(self.specialists)
        if settings.venture_in_chat:
            ceo_roster.update(self.venture_team)

        self.ceo = agent(
            "ceo",
            "CEO",
            "Orchestrator: routes requests to specialists (in parallel) and synthesizes.",
            "#a78bfa",
            CEO_SYSTEM_PROMPT,
            _registry(self._make_roster_tool(), self._make_delegate_tool(ceo_roster)),
            ["get_agent_roster", "delegate_to_agent"],
        )

    def all_agents(self) -> list[Agent]:
        return [
            self.ceo,
            *self.specialists.values(),
            *self.finance_team.values(),
            *self.content_team.values(),
            *self.venture_team.values(),
        ]

    # ------------------------------------------------------------------ client

    def _default_client_factory(self):
        if self.settings.demo_mode:
            from app.agents.simulated import SimulatedClient

            return SimulatedClient()
        import anthropic

        return anthropic.AsyncAnthropic()

    def _get_client(self):
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    # ------------------------------------------------------------------- tools

    def _make_roster_tool(self) -> Tool:
        service = self

        async def handler(tool_input: dict, ctx: ToolContext) -> str:
            return _roster_text(service.specialists)

        return Tool(
            name="get_agent_roster",
            description="List the specialist agents you can delegate to, with their expertise.",
            input_schema={"type": "object", "properties": {}},
            handler=handler,
        )

    def _make_delegate_tool(self, roster: dict[str, Agent]) -> Tool:
        """Delegation tool over a specific roster — used by the CEO (specialists)
        and by the CFO (its finance sub-team)."""
        service = self

        async def handler(tool_input: dict, ctx: ToolContext) -> str:
            name = (tool_input.get("agent") or "").strip().lower()
            task = (tool_input.get("task") or "").strip()
            if not task:
                return "Delegation failed: empty task."
            agent = roster.get(name)
            if agent is None:
                return f"Delegation failed: no agent named {name!r}. {_roster_text(roster)}"
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

        return Tool(
            name="delegate_to_agent",
            description=(
                "Delegate a self-contained task to a specialist agent and get their "
                "answer back. To parallelize, emit several delegate_to_agent calls "
                "in one response.\n" + _roster_text(roster)
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": sorted(roster.keys()),
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
