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


# ------------------------------------------------- venture-layer playbooks
# Venture agents are prompt-driven, so demo mode cans structured reasoning in
# each agent's required output format while every tool call (score_idea,
# save_memory) stays real. The canned text is honest about being canned.

VENTURE_DEMO_NOTE = (
    "_(Demo mode: template reasoning in the agent's required format — a live "
    "model replaces this with real analysis.)_"
)


def _topic(task: str) -> str:
    """Workflow briefs carry a 'TOPIC: …' line; fall back to the first line."""
    for line in task.splitlines():
        if line.strip().upper().startswith("TOPIC:"):
            return line.split(":", 1)[1].strip()
    first = task.strip().splitlines()[0] if task.strip() else "the proposal"
    return first[:120]


def _canned(text: str):
    return [_text(f"{text}\n\n{VENTURE_DEMO_NOTE}")], "end_turn"


def _handle_venture_ceo(turn: int, messages: list[dict]):
    task = _last_user_text(messages)
    topic = _topic(task)
    if "revise" in task.lower() and "objection" in task.lower():
        return _canned(
            f"## Revised plan\nScope of {topic!r} cut to a small pilot: the finance "
            "objection (unproven unit economics) is answered by pre-selling before "
            "building; the demand objection by 10 discovery calls in week 1; the "
            "feasibility and execution objections by dropping custom builds for "
            "no-code tools.\n\n"
            "## Final decision\nProceed as a 30-day pilot with pre-sales as the gate "
            "— not a full launch.\n\n"
            "## Remaining risks\n- Pilot interest may not convert to paid (owner: COO)\n"
            "- Regulatory questions stay open until reviewed (owner: Risk Officer)\n\n"
            "## Execution steps\n1. List 100 prospects and start outreach (week 1)\n"
            "2. Pre-sell to 3 before building anything (weeks 1-2)\n"
            "3. Deliver a manual pilot to the first payer (weeks 3-4)\n\n"
            "## Owner\nFounder\n\n## Deadline\n30 days\n\n"
            "Would reverse if: fewer than 3 discovery calls booked by day 10."
        )
    return _canned(
        f"## Proposal\nStrategy for {topic!r}: start with the narrowest viable "
        "niche, one concrete offer at a fixed monthly price, one acquisition "
        "channel (direct outreach), and a 30-day timeline to first revenue.\n\n"
        "Key numbers: budget split 70% delivery / 30% acquisition; target 3 "
        "paying customers in 30 days.\n\n"
        "Assumptions (numbered for attack):\n"
        "1. The niche feels this pain weekly and will take a call about it.\n"
        "2. One founder can deliver the offer alongside sales.\n"
        "3. Price clears the founder's minimum viable income at 10 customers.\n\n"
        "First 3 steps: (1) list 100 prospects, (2) book 5 discovery calls, "
        "(3) pre-sell before building."
    )


def _handle_venture_cfo(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Financial objections to {topic!r}:\n"
        "1. Customer-acquisition cost is assumed, not measured — if it is 2x the "
        "assumption, the budget buys ~2 customers, not a business.\n"
        "2. Cash timing ignored: revenue arrives after delivery, tools and ads "
        "bill up front.\n"
        "3. Price point has no anchor — no comparable offer is cited.\n\n"
        "Numbers the plan is missing: CAC target, gross margin after tool costs, "
        "founder minimum monthly income.\n"
        "Cheapest validation of the worst assumption: pre-sell to 3 prospects "
        "before building (cost ~0, one week).\n"
        "Verdict: fund with conditions — 1 pre-sale within 10 days or stop."
    )


def _handle_venture_cmo(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Demand & positioning objections to {topic!r}:\n"
        "1. Demand is asserted, not evidenced — no payments, pre-orders or "
        "replies are cited. What would prove it: 10 discovery calls where 4+ "
        "name this as a top-3 problem.\n"
        "2. The target customer is too broad to reach with one message.\n"
        "3. The channel plan lacks arithmetic (cost per lead x conversion → CAC "
        "vs. customer value).\n\n"
        "Target customer as stated: too close to 'everyone' — pick one niche.\n"
        "Strongest channel hypothesis + math: direct outreach to 100 named "
        "prospects; at 15% reply and 20% close → 3 customers, CAC ≈ founder "
        "time only.\n"
        "Verdict: demand imagined — run the discovery calls before building."
    )


def _handle_venture_cto(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Feasibility objections to {topic!r}:\n"
        "1. Third-party approvals (payment/API/platform access) take 1-3 weeks; "
        "the plan assumes zero days.\n"
        "2. The stated build scope is the full vision, not the minimal promise "
        "— at the founder's skill level, budget 2x the stated time.\n"
        "3. No fallback is named for the AI-dependent step.\n\n"
        "Minimal build that delivers the promise: no-code intake + one automated "
        "workflow + manual review behind the scenes; ~1 week.\n"
        "Riskiest technical assumption + ≤3-day prototype: that the critical "
        "integration allows what the plan needs — wire it end-to-end with dummy "
        "data first.\n"
        "Verdict: buildable with cuts."
    )


def _handle_coo(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Execution plan: first paying customer for {topic!r} in 30 days.\n"
        "Capacity assumption: 20 focused hours/week, existing skills only.\n\n"
        "Week 1: Founder — list 100 prospects (done = sheet with contact + "
        "reason-to-buy); Founder — contact 20, book 5 calls (done = 5 in "
        "calendar). Week 2: run calls; send one-page offer to all 5. Week 3: "
        "manual pilot for the first yes. Week 4: convert pilot to paid; ask for "
        "2 referrals.\n\n"
        "Dependencies & lead times: any platform/API approval filed on day 1.\n"
        "Weekly checkpoint metric: calls booked (wk1: 5) → offers sent (wk2: 5) "
        "→ pilots live (wk3: 1) → paid (wk4: 1).\n"
        "Kill criteria: <2 calls booked by day 10 → change niche or channel.\n"
        "Top execution risk: founder time collapses — pre-block calling slots "
        "in the calendar now."
    )


def _handle_risk(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Risk assessment: {topic!r} (jurisdiction: founder's home market — "
        "verify).\n"
        "1. Regulatory surface — regulatory. Likelihood M, severity H. Trigger: "
        "the offer touches a regulated activity (health/finance/data). "
        "Mitigation: position as tooling, not advice; minimize data collected; "
        "written scope. → residual M/L.\n"
        "2. Platform dependency — operational. Likelihood M, severity M. "
        "Trigger: a policy change on the main channel/API. Mitigation: keep an "
        "owned contact list and a fallback channel. → residual L.\n"
        "3. Reputational — worst screenshot: an automated message going wrong "
        "in public. Mitigation: human review on outward-facing sends (the "
        "Approvals inbox already enforces this).\n\n"
        "Fatal-if-ignored: operating a licensed activity without checking — "
        "verify before selling.\n"
        "Requires professional review: client contract template (lawyer, one-time).\n"
        "Overall: proceed with mitigations.\n"
        "This is risk triage, not legal advice."
    )


def _handle_red_team(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Red-team findings for {topic!r} (worst first):\n"
        "1. Weak assumption: people who complain will pay.\n"
        "   Why it matters: the entire revenue model rests on it.\n"
        "   Evidence needed: 3 pre-sales or signed pilots.\n"
        "   Failure scenario: 30 days of building, zero payers, morale gone.\n"
        "   Severity: fatal. Fix: pre-sell before building.\n"
        "2. Weak assumption: the founder can sell and deliver simultaneously.\n"
        "   Evidence needed: a week-1 calendar that actually fits both.\n"
        "   Severity: serious. Fix: cut delivery scope to manual-first.\n"
        "3. Weak assumption: no incumbent responds.\n"
        "   Evidence needed: what the top 3 alternatives ship this quarter.\n"
        "   Severity: manageable. Fix: pick a niche too small for them.\n\n"
        "Revised recommendation: pursue only as a pre-sold, manual-first pilot; "
        "kill it if nobody pre-pays in 2 weeks."
    )


def _handle_sales(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    return _canned(
        f"Persona: the owner-operator losing hours weekly to the problem behind "
        f"{topic!r}; current solution: doing it manually.\n"
        "Offer: outcome delivered in 7 days, fixed monthly price, first 2 weeks "
        "free, 3 pilot slots.\n\n"
        "Copy (cold email, ≤120 words):\n"
        "Subject: your Tuesday afternoons\n"
        "Hi — businesses like yours lose hours every week to this exact task. "
        "We take it off your plate in 7 days; you check results in a weekly "
        "2-line email. First 2 weeks free, and if it doesn't save real time, "
        "don't pay. Worth a 10-minute call Thursday?\n\n"
        "Why this works: opens on their cost, not the product; risk reversed; "
        "one CTA with a specific day.\n"
        "Objections pre-handled: 'too technical' → done-for-you in 7 days; "
        "'cost' → free pilot.\n"
        "A/B variant subject: '2 hours back, every week'."
    )


_DEMO_PERSONA_TYPES = [
    ("Skeptical veteran", 3, "has seen tools like this fail before"),
    ("Overwhelmed owner", 8, "drowning in the manual version of this task"),
    ("Price-sensitive starter", 5, "wants it but budgets in the hundreds"),
    ("Happy with current tool", 2, "sees no reason to switch"),
    ("Early adopter", 7, "tries everything new in the space"),
]


def _handle_interviewer(turn: int, messages: list[dict]):
    topic = _topic(_last_user_text(messages))
    personas = []
    for i in range(20):
        kind, likelihood, stance = _DEMO_PERSONA_TYPES[i % len(_DEMO_PERSONA_TYPES)]
        personas.append(
            f"{i + 1}. {kind} — {stance}. Frustration {min(likelihood + 1, 10)}/10; "
            f"budget scales with business size; buying trigger: a visible weekly "
            f"loss; objection: \"how is this different from what I do now?\"; "
            f"likelihood to buy {likelihood}/10; best angle: show the hours lost."
        )
    body = (
        f"SYNTHETIC customer interviews for {topic!r} — 20 simulated personas "
        "(demo mode cycles 5 archetypes; a live model writes 20 distinct "
        "ones):\n\n" + "\n".join(personas) + "\n\n"
        "Synthesis:\n"
        "- Common pain: recurring manual work with a visible weekly cost.\n"
        "- Repeated objection: differentiation from the status quo.\n"
        "- Strongest segment: overwhelmed owner-operators; weakest: users happy "
        "with current tools.\n"
        "- Most promising offer: done-for-you pilot with risk reversal.\n"
        "- Best pricing angle: priced against hours saved.\n"
        "- Best landing message: name the weekly loss, promise the outcome in "
        "7 days.\n\n"
        "These are SYNTHETIC interviews — validate with at least 10 real "
        "customer conversations before building."
    )
    return _canned(body)


# Conservative mid-range scores: the deterministic engine turns these into a
# TEST FIRST verdict — the honest default for an unvalidated idea.
_DEMO_SCORES = {
    "market_demand": 6, "ease_of_mvp": 6, "speed_to_revenue": 6,
    "competition_level": 5, "founder_fit": 5, "distribution_advantage": 4,
    "technical_complexity": 6, "legal_regulatory_risk": 6, "capital_required": 7,
    "scalability": 6, "profit_margin": 6, "defensibility": 4,
    "time_to_first_customer": 5, "risk_adjusted_upside": 5,
}


def _handle_scorer(turn: int, messages: list[dict]):
    task = _last_user_text(messages)
    topic = _topic(task)
    if turn == 0:
        return [
            _tool_use(
                "score_idea",
                {
                    "title": topic[:200],
                    "description": task.strip()[:1800],
                    "scores": dict(_DEMO_SCORES),
                    "rationales": {
                        key: "Demo-mode conservative estimate; replace with "
                        "evidence-based scoring on a live model."
                        for key in _DEMO_SCORES
                    },
                    "best_version": "The narrowest niche variant of the idea, "
                    "pre-sold before building.",
                    "worst_risk": "Demand is assumed, not evidenced.",
                    "validation_test": "Pre-sell to 3 prospects in one week at "
                    "near-zero cost.",
                    "next_actions": [
                        "List 100 named prospects in one niche",
                        "Book 5 discovery calls this week",
                        "Pre-sell a pilot before building anything",
                    ],
                },
            )
        ], "tool_use"
    results = _last_tool_results(messages)
    return [_text("\n\n".join(results) + f"\n\n{VENTURE_DEMO_NOTE}")], "end_turn"


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
    # venture layer
    "venture_ceo": _handle_venture_ceo,
    "venture_cfo": _handle_venture_cfo,
    "venture_cmo": _handle_venture_cmo,
    "venture_cto": _handle_venture_cto,
    "coo": _handle_coo,
    "risk": _handle_risk,
    "red_team": _handle_red_team,
    "sales": _handle_sales,
    "interviewer": _handle_interviewer,
    "scorer": _handle_scorer,
}

_MARKERS = [
    ("CEO orchestrator", "ceo"),
    ("You are the CFO", "cfo"),
    ("FP&A agent", "fpa"),
    ("Reporting agent", "reporting"),
    ("Revenue agent", "revenue"),
    ("Control agent", "control"),
    # Venture markers sit before the operations "CMO agent"/"CTO agent"
    # entries so a venture-skeptic prompt can never fall through to an
    # operations handler; none of these phrases appears in any other prompt.
    ("venture strategist", "venture_ceo"),
    ("financial skeptic", "venture_cfo"),
    ("demand skeptic", "venture_cmo"),
    ("feasibility skeptic", "venture_cto"),
    ("COO agent", "coo"),
    ("Risk Officer agent", "risk"),
    ("Red Team agent", "red_team"),
    ("Sales agent", "sales"),
    ("Interviewer agent", "interviewer"),
    ("Idea Scorer agent", "scorer"),
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
