"""Demo mode: a zero-cost stand-in for the Anthropic API.

SimulatedClient mimics AsyncAnthropic.messages.create just well enough to
drive the real Agent loop: rule-based routing decides which specialists to
delegate to and which canned SQL to run, but every tool call is REAL — the
queries hit the live database, drafts land in the real Approvals inbox,
reports persist to the real library. Only the free-form reasoning is canned.

Enable with DEMO_MODE=1 (no ANTHROPIC_API_KEY needed). Token usage is
reported as zero because nothing is spent.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

# --------------------------------------------------------------- primitives


def _text(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use(name: str, tool_input: dict) -> SimpleNamespace:
    return SimpleNamespace(
        type="tool_use", id=f"sim_{uuid.uuid4().hex[:10]}", name=name, input=tool_input
    )


def _response(blocks: list, stop_reason: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=0,
            output_tokens=0,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
    )


def _last_user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            return message["content"]
    return ""


def _last_tool_results(messages: list[dict]) -> list[str]:
    if not messages:
        return []
    content = messages[-1].get("content")
    if not isinstance(content, list):
        return []
    return [
        str(block.get("content", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]


def _n_assistant_turns(messages: list[dict]) -> int:
    return sum(1 for m in messages if m.get("role") == "assistant")


DEMO_NOTE = "_(Demo mode: rule-based routing with live SQL — no API spend.)_"

# ----------------------------------------------------------------- routing

_BROAD = ["how is the business", "how's the business", "business doing", "state of the business"]
_CEO_ROUTES = [
    ("cmo", ["draft", "announce", "content", "post ", "email", "social", "cac",
             "campaign", "channel", "marketing", "lead", "acquisition", "signup"]),
    ("cfo", ["profit", "runway", "revenue", "burn", "cash", "invoice", "expense",
             "mrr", "payroll", "salar", "p&l", "pnl", "financ", "forecast", "budget",
             "reconcil", "anomal", "unusual", "report"]),
    ("cto", ["project", "engineering", "on track", "deadline", "launch", "v2", "ship"]),
    ("coordinator", ["blocked", "task", "overdue", "workflow"]),
    ("researcher", ["competitor", "market", "industry", "benchmark", "landscape"]),
]

_CFO_ROUTES = [
    ("reporting", ["report", "p&l", "pnl", "statement", "document"]),
    ("control", ["reconcil", "anomal", "unusual", "add up", "check", "audit", "duplicate"]),
    ("revenue", ["invoice", "overdue", "receivable", "collections", "ar ", "churn", "expansion", "movement"]),
]

_CONTENT_WORDS = ["draft", "announce", "write", "post", "email", "social", "content", "copy"]


def _route_ceo(task: str) -> list[str]:
    lowered = task.lower()
    if any(phrase in lowered for phrase in _BROAD):
        return ["cfo", "cmo", "cto", "coordinator"]
    targets = [name for name, words in _CEO_ROUTES if any(w in lowered for w in words)]
    return targets or ["cfo"]


def _route_cfo(task: str) -> str:
    lowered = task.lower()
    for name, words in _CFO_ROUTES:
        if any(w in lowered for w in words):
            return name
    return "fpa"


# ------------------------------------------------------------ leaf playbooks

_LEAF_QUERIES: dict[str, tuple[list[str], str]] = {
    "fpa": (
        [
            "SELECT strftime('%Y-%m', date) AS month, "
            "ROUND(SUM(CASE WHEN type='revenue' THEN amount ELSE 0 END), 0) AS revenue, "
            "ROUND(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expenses, "
            "ROUND(SUM(CASE WHEN type='revenue' THEN amount ELSE -amount END), 0) AS profit "
            "FROM transactions GROUP BY month ORDER BY month DESC LIMIT 6",
            "SELECT key, value FROM meta WHERE key IN ('starting_cash', 'window_end')",
            "SELECT COUNT(*) AS active_customers, ROUND(SUM(mrr), 0) AS mrr "
            "FROM customers WHERE churn_date IS NULL",
        ],
        "FP&A summary from live data (most recent months first). Profit = revenue − "
        "expenses per month; runway ≈ (starting_cash + cumulative profit) ÷ average "
        "burn of the last 3 months.",
    ),
    "revenue": (
        [
            "SELECT status, COUNT(*) AS invoices, ROUND(SUM(amount), 0) AS value "
            "FROM invoices GROUP BY status",
            "SELECT c.name, i.amount, i.due_date FROM invoices i "
            "JOIN customers c ON c.id = i.customer_id "
            "WHERE i.status = 'overdue' ORDER BY i.due_date LIMIT 10",
        ],
        "Accounts-receivable picture from live data: totals by invoice status, then "
        "the oldest overdue invoices.",
    ),
    "control": (
        [
            "SELECT strftime('%Y-%m', date) AS month, ROUND(SUM(amount), 2) AS subscription_revenue, "
            "COUNT(*) AS charges, COUNT(DISTINCT customer_id) AS customers "
            "FROM transactions WHERE category = 'subscription' "
            "GROUP BY month ORDER BY month DESC LIMIT 1",
            "SELECT strftime('%Y-%m', date) AS month, ROUND(SUM(amount), 2) AS payroll, "
            "COUNT(*) AS payslips FROM transactions WHERE category = 'salary' "
            "GROUP BY month ORDER BY month DESC LIMIT 1",
            "SELECT COUNT(*) AS mismatched_campaigns FROM campaigns c WHERE ABS("
            "(SELECT COALESCE(SUM(t.amount), 0) FROM transactions t "
            "WHERE t.campaign_id = c.id AND t.category = 'marketing') - c.spend) > 0.01",
            "SELECT COUNT(*) AS overdue_invoices, ROUND(COALESCE(SUM(amount), 0), 0) "
            "AS overdue_value FROM invoices WHERE status = 'overdue'",
        ],
        "Control check on live data. Reading the results: charges must equal customers "
        "(one charge per active customer last month) → [OK] if equal; "
        "mismatched_campaigns must be 0 → [OK]; payroll and overdue detail above.",
    ),
    "cto": (
        [
            "SELECT name, status, deadline FROM projects "
            "ORDER BY CASE status WHEN 'at_risk' THEN 0 WHEN 'active' THEN 1 ELSE 2 END, deadline",
            "SELECT title, blocked_reason FROM tasks "
            "WHERE status = 'blocked' AND department IN ('Engineering', 'Product')",
        ],
        "Engineering status from live data: projects (at-risk first), then blocked "
        "engineering/product work with reasons.",
    ),
    "coordinator": (
        [
            "SELECT t.title, t.department, t.blocked_reason, e.name AS assignee "
            "FROM tasks t LEFT JOIN employees e ON e.id = t.assignee_id "
            "WHERE t.status = 'blocked'",
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status",
        ],
        "Workflow picture from live data: every blocked task with its reason and "
        "assignee, then task counts by status.",
    ),
    "cmo": (
        [
            "SELECT channel, ROUND(SUM(spend), 0) AS spend, SUM(conversions) AS conversions, "
            "ROUND(SUM(spend) / MAX(SUM(conversions), 1), 0) AS cac "
            "FROM campaigns GROUP BY channel ORDER BY cac",
            "SELECT strftime('%Y-%m', signup_date) AS month, COUNT(*) AS signups "
            "FROM customers GROUP BY month ORDER BY month DESC LIMIT 6",
        ],
        "Marketing performance from live data: CAC by channel (lowest first; spend ÷ "
        "attributed conversions), then the recent signup trend.",
    ),
}


def _leaf_playbook(agent: str, turn: int, messages: list[dict]):
    queries, closing = _LEAF_QUERIES[agent]
    if turn == 0:
        return [_tool_use("sql_query", {"query": q}) for q in queries], "tool_use"
    results = _last_tool_results(messages)
    body = "\n\n".join(results)
    return [_text(f"{closing}\n\n{body}\n\n{DEMO_NOTE}")], "end_turn"


# ------------------------------------------------------------ agent handlers


def _handle_ceo(turn: int, messages: list[dict]):
    task = _last_user_text(messages)
    if turn == 0:
        targets = _route_ceo(task)
        return [
            _tool_use("delegate_to_agent", {"agent": t, "task": task}) for t in targets
        ], "tool_use"
    results = _last_tool_results(messages)
    body = "\n\n".join(results)
    return [_text(f"Executive synthesis {DEMO_NOTE}\n\n{body}")], "end_turn"


def _handle_cfo(turn: int, messages: list[dict]):
    task = _last_user_text(messages)
    if turn == 0:
        return [_tool_use("delegate_to_agent", {"agent": _route_cfo(task), "task": task})], "tool_use"
    results = _last_tool_results(messages)
    return [_text("Finance summary from my sub-team:\n\n" + "\n\n".join(results))], "end_turn"


def _handle_cmo(turn: int, messages: list[dict]):
    task = _last_user_text(messages)
    if any(w in task.lower() for w in _CONTENT_WORDS):
        if turn == 0:
            return [_tool_use("delegate_to_agent", {"agent": "content", "task": task})], "tool_use"
        results = _last_tool_results(messages)
        return [_text("\n\n".join(results) + "\n\nThe draft is waiting in the Approvals inbox.")], "end_turn"
    return _leaf_playbook("cmo", turn, messages)


def _handle_reporting(turn: int, messages: list[dict]):
    if turn == 0:
        queries, _ = _LEAF_QUERIES["fpa"]
        return [_tool_use("sql_query", {"query": queries[0]})], "tool_use"
    if turn == 1:
        results = _last_tool_results(messages)
        table = results[0] if results else "(no data)"
        return [
            _tool_use(
                "report_writer",
                {
                    "title": "P&L summary (demo mode)",
                    "sections": [
                        {"heading": "Monthly P&L — live data", "content": table},
                        {
                            "heading": "Notes",
                            "content": "Generated in demo mode: figures come straight "
                            "from SQL; narrative analysis requires a live model "
                            "(set ANTHROPIC_API_KEY).",
                        },
                    ],
                },
            )
        ], "tool_use"
    results = _last_tool_results(messages)
    return [_text("\n\n".join(results) + f"\n\n{DEMO_NOTE}")], "end_turn"


def _handle_content(turn: int, messages: list[dict]):
    task = _last_user_text(messages)
    if turn == 0:
        lowered = task.lower()
        channel = (
            "email" if "email" in lowered
            else "social" if "social" in lowered or "post" in lowered
            else "blog" if "blog" in lowered
            else "announcement"
        )
        body = (
            f"**Draft ({channel}) — generated in demo mode**\n\n"
            f"Brief: {task.strip()}\n\n"
            "Lumina Labs helps 12-person-to-enterprise teams see their product data "
            "clearly. Today we're sharing an update our customers asked for — see the "
            "brief above for the specifics. Existing customers keep their current "
            "pricing, and everything ships to all plans (starter $99, growth $299, "
            "scale $899).\n\n"
            "_Demo mode writes template copy; a live model (ANTHROPIC_API_KEY) writes "
            "the real thing. Either way, nothing publishes without approval._"
        )
        return [
            _tool_use(
                "content_writer",
                {"title": f"Draft: {task.strip()[:80]}", "channel": channel, "body": body},
            )
        ], "tool_use"
    results = _last_tool_results(messages)
    return [_text("\n\n".join(results))], "end_turn"


def _handle_researcher(turn: int, messages: list[dict]):
    return [
        _text(
            "(Demo mode) External web research needs a live Anthropic API key — I "
            "cannot browse the web for free. Set ANTHROPIC_API_KEY and remove "
            "DEMO_MODE to enable competitor scans. Everything database-backed still "
            "works in demo mode."
        )
    ], "end_turn"


_HANDLERS = {
    "ceo": _handle_ceo,
    "cfo": _handle_cfo,
    "cmo": _handle_cmo,
    "reporting": _handle_reporting,
    "content": _handle_content,
    "researcher": _handle_researcher,
    "fpa": lambda turn, messages: _leaf_playbook("fpa", turn, messages),
    "revenue": lambda turn, messages: _leaf_playbook("revenue", turn, messages),
    "control": lambda turn, messages: _leaf_playbook("control", turn, messages),
    "cto": lambda turn, messages: _leaf_playbook("cto", turn, messages),
    "coordinator": lambda turn, messages: _leaf_playbook("coordinator", turn, messages),
}

_MARKERS = [
    ("CEO orchestrator", "ceo"),
    ("You are the CFO", "cfo"),
    ("FP&A agent", "fpa"),
    ("Reporting agent", "reporting"),
    ("Revenue agent", "revenue"),
    ("Control agent", "control"),
    ("CMO agent", "cmo"),
    ("CTO agent", "cto"),
    ("Researcher agent", "researcher"),
    ("Workflow Coordinator", "coordinator"),
    ("Content agent", "content"),
]


class _SimulatedMessages:
    async def create(self, *, model, max_tokens, system, tools, messages):
        agent = next((name for marker, name in _MARKERS if marker in system), None)
        if agent is None:
            return _response([_text("(Demo mode) I don't have a playbook for this agent.")], "end_turn")
        turn = _n_assistant_turns(messages)
        try:
            blocks, stop_reason = _HANDLERS[agent](turn, messages)
        except Exception as exc:  # defensive: never take the loop down
            return _response([_text(f"(Demo mode) playbook error: {exc}")], "end_turn")
        return _response(blocks, stop_reason)


class SimulatedClient:
    """Drop-in for anthropic.AsyncAnthropic in demo mode."""

    def __init__(self):
        self.messages = _SimulatedMessages()
