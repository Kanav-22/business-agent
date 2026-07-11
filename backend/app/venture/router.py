"""Prompt Router — deterministic routing of free-text requests to agents and
workflows. The human-readable mirror is docs/ROUTING_RULES.md; keep them in sync.

Design: keyword rules, not a model call — cheap, auditable, and identical in
demo and live mode. The LLM-driven CEO routing in chat is untouched; this
router powers POST /api/route, the Venture Studio, and workflow pre-flights.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.engine import Engine

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass
class RouteRule:
    category: str
    keywords: list[str]
    primary_agent: str
    supporting_agents: list[str]
    workflow: list[str]
    risk_level: str  # base level; domain modifiers can only escalate
    reason: str
    required_inputs: list[str]
    expected_output: str


@dataclass
class RouteDecision:
    category: str
    primary_agent: str
    supporting_agents: list[str]
    workflow: list[str]
    risk_level: str
    reason: str
    required_inputs: list[str]
    expected_output: str
    matched_categories: list[str] = field(default_factory=list)
    founder_fit_note: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "primary_agent": self.primary_agent,
            "supporting_agents": self.supporting_agents,
            "workflow": self.workflow,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "required_inputs": self.required_inputs,
            "expected_output": self.expected_output,
            "matched_categories": self.matched_categories,
            "founder_fit_note": self.founder_fit_note,
            "warnings": self.warnings,
        }


RULES: list[RouteRule] = [
    RouteRule(
        category="business_idea_validation",
        keywords=["idea", "validate", "should i start", "should i build", "want to launch",
                  "want to start", "new business", "is it worth", "worth pursuing", "opportunity"],
        primary_agent="ceo",
        supporting_agents=["scorer", "researcher", "red_team", "interviewer"],
        workflow=["idea_score", "interviews", "failure_sim", "debate"],
        risk_level="medium",
        reason="A new idea needs strict scoring, synthetic customer evidence, an "
               "adversarial pass and a debate before any build commitment.",
        required_inputs=["idea description", "budget", "timeline", "founder skills"],
        expected_output="Go / No-Go / Test-First verdict with a validation plan",
    ),
    RouteRule(
        category="product_building",
        keywords=["build", "mvp", "prototype", "develop", "feature", "product plan",
                  "ship", "scope"],
        primary_agent="venture_cto",
        supporting_agents=["coo", "researcher"],
        workflow=["mvp_scope", "build_plan", "weekly_checkpoints"],
        risk_level="medium",
        reason="Building consumes the scarcest resources (time, capital); scope and "
               "feasibility must be pressure-tested before code.",
        required_inputs=["validated idea", "capacity (hours/skills)", "deadline"],
        expected_output="Scoped MVP with a concrete stack and execution plan",
    ),
    RouteRule(
        category="marketing",
        keywords=["marketing", "campaign", "channel", "cac", "ads", "seo", "content plan",
                  "acquisition", "leads", "audience", "brand"],
        primary_agent="venture_cmo",
        supporting_agents=["researcher", "sales"],
        workflow=["audience_definition", "channel_math", "experiment_design", "approvals"],
        risk_level="low",
        reason="Marketing plans need channel arithmetic and an experiment design, "
               "not channel lists; outward content still passes the Approvals inbox.",
        required_inputs=["target customer", "budget", "current numbers"],
        expected_output="Channel plan with CAC math and a first experiment",
    ),
    RouteRule(
        category="sales",
        keywords=["sales", "sell", "outreach", "cold email", "cold call", "landing page",
                  "copy", "offer", "pitch", "close", "objection", "convert"],
        primary_agent="sales",
        supporting_agents=["venture_cmo"],
        workflow=["icp_confirmation", "offer_design", "copy_draft", "approvals"],
        risk_level="low",
        reason="Copy converts only when the persona, offer and objections are "
               "explicit — the Sales agent produces all three together.",
        required_inputs=["ICP", "offer", "available proof/assets"],
        expected_output="Channel-formatted copy with objection handling and an A/B variant",
    ),
    RouteRule(
        category="finance",
        keywords=["profit", "runway", "burn", "cash", "revenue", "budget", "forecast",
                  "invoice", "mrr", "expense", "p&l", "unit economics", "margin"],
        primary_agent="cfo",
        supporting_agents=[],
        workflow=["cfo_subteam_routing"],
        risk_level="low",
        reason="Finance questions route to the CFO, whose sub-team grounds every "
               "number in the database.",
        required_inputs=["the question", "timeframe"],
        expected_output="Grounded numbers with per-agent attribution",
    ),
    RouteRule(
        category="legal_compliance",
        keywords=["legal", "compliance", "regulation", "license", "gdpr", "privacy",
                  "terms", "contract", "liability", "lawsuit", "copyright", "trademark"],
        primary_agent="risk",
        supporting_agents=["researcher"],
        workflow=["risk_assessment", "professional_review_list", "mitigation_plan"],
        risk_level="high",
        reason="Legal exposure is asymmetric: cheap to check early, expensive to "
               "discover late. The Risk Officer ranks and routes to professionals.",
        required_inputs=["jurisdiction", "data handled", "claims made"],
        expected_output="Ranked risk register with a proceed/don't verdict",
    ),
    RouteRule(
        category="hiring",
        keywords=["hire", "hiring", "recruit", "employee", "contractor", "freelancer",
                  "team member", "delegate work"],
        primary_agent="coo",
        supporting_agents=["cfo", "risk"],
        workflow=["role_definition", "cost_model", "hiring_plan"],
        risk_level="medium",
        reason="A hire is a recurring cost and a legal relationship; the COO scopes "
               "the role, the CFO prices it, Risk checks the employment terms.",
        required_inputs=["role", "budget", "timeline"],
        expected_output="Hire/don't-hire recommendation with a costed plan",
    ),
    RouteRule(
        category="fundraising",
        keywords=["fundraise", "investor", "raise money", "seed round", "vc", "angel",
                  "pitch deck", "term sheet", "valuation"],
        primary_agent="ceo",
        supporting_agents=["cfo", "researcher", "risk", "red_team"],
        workflow=["readiness_check", "numbers_pack", "narrative", "red_team_review"],
        risk_level="high",
        reason="Fundraising trades ownership for capital and locks in obligations; "
               "the deck must survive a red-team pass before an investor sees it.",
        required_inputs=["metrics", "runway", "raise target"],
        expected_output="Readiness verdict and a materials plan",
    ),
    RouteRule(
        category="customer_support",
        keywords=["support", "complaint", "refund", "ticket", "customer issue",
                  "unhappy customer", "churn reason"],
        primary_agent="coo",
        supporting_agents=["venture_cto"],
        workflow=["issue_triage", "process_fix", "automation_check"],
        risk_level="low",
        reason="Support problems are process problems first; the COO fixes the "
               "process, then checks what should be automated.",
        required_inputs=["issue volume", "current process"],
        expected_output="Support process with automation candidates",
    ),
    RouteRule(
        category="growth",
        keywords=["growth", "growing", "stalled", "plateau", "scale up", "more customers",
                  "retention", "churn is", "funnel"],
        primary_agent="venture_cmo",
        supporting_agents=["cfo", "researcher", "red_team"],
        workflow=["funnel_diagnosis", "bottleneck_math", "experiment_plan"],
        risk_level="medium",
        reason="Growth problems are diagnosed in the funnel numbers before choosing "
               "tactics; the red team checks the diagnosis isn't wishful.",
        required_inputs=["funnel numbers", "churn", "CAC"],
        expected_output="Diagnosed bottleneck with ranked experiments",
    ),
    RouteRule(
        category="pivot",
        keywords=["pivot", "change direction", "shut down", "give up", "not working",
                  "switch to", "abandon"],
        primary_agent="ceo",
        supporting_agents=["red_team", "cfo", "venture_cmo", "researcher"],
        workflow=["debate", "failure_sim", "decision_memory"],
        risk_level="high",
        reason="Pivots throw away compounding progress; the decision needs a full "
               "debate plus a failure simulation of the NEW direction.",
        required_inputs=["current traction", "pivot hypothesis", "runway"],
        expected_output="Pivot/persevere decision with a reversal trigger",
    ),
    RouteRule(
        category="market_research",
        keywords=["market research", "market size", "competitor", "competitors", "industry",
                  "trends", "benchmark", "landscape", "who else"],
        primary_agent="researcher",
        supporting_agents=[],
        workflow=["research_brief", "cited_findings", "memory_save"],
        risk_level="low",
        reason="External questions go to the Researcher: cited findings with "
               "explicit confidence, saved to memory for reuse.",
        required_inputs=["the falsifiable question"],
        expected_output="Cited findings with a confidence level",
    ),
    RouteRule(
        category="technical_architecture",
        keywords=["architecture", "tech stack", "database", "framework", "infra",
                  "hosting", "api design", "which technology", "scalab"],
        primary_agent="venture_cto",
        supporting_agents=["risk"],
        workflow=["requirements", "buy_vs_build", "architecture_note"],
        risk_level="medium",
        reason="Architecture choices are expensive to reverse; buy-vs-build and the "
               "riskiest component get decided explicitly.",
        required_inputs=["scale expectations", "team skills", "budget"],
        expected_output="Stack decision plus a riskiest-component prototype plan",
    ),
    RouteRule(
        category="trading_business_risk",
        keywords=["trading", "trade", "invest", "portfolio", "leverage", "options",
                  "crypto", "bet the", "all in", "exposure"],
        primary_agent="risk",
        supporting_agents=["cfo", "red_team"],
        workflow=["risk_assessment", "exposure_math", "debate"],
        risk_level="high",
        reason="Capital-at-risk decisions get the Risk Officer first: exposure math "
               "and worst-case sizing before any strategy discussion.",
        required_inputs=["capital at risk", "instruments/commitments", "jurisdiction"],
        expected_output="Exposure register with a proceed/don't verdict",
    ),
    RouteRule(
        category="board_review",
        keywords=["board meeting", "board review", "quarterly review", "big decision",
                  "major decision", "debate this", "challenge this plan", "devil's advocate"],
        primary_agent="ceo",
        supporting_agents=["venture_cfo", "venture_cmo", "venture_cto", "coo", "risk", "researcher"],
        workflow=["debate"],
        risk_level="medium",
        reason="Major decisions run the full debate: every executive attacks from "
               "their domain before the CEO decides.",
        required_inputs=["the proposal or period to review"],
        expected_output="Board-format report (proposal, objections, revision, decision, owner, deadline)",
    ),
]

# Domain modifiers: these keywords escalate risk to HIGH and pull in the Risk
# Officer, whatever the base category — regulated or trust-critical domains.
HIGH_RISK_DOMAINS = {
    "healthcare": ["doctor", "medical", "health", "clinic", "patient", "hospital",
                   "pharma", "therapy", "diagnos"],
    "finance_regulated": ["loan", "lending", "insurance", "banking", "payment",
                          "invest", "trading", "crypto", "securities"],
    "children": ["kids", "children", "minor", "school", "student data"],
    "legal_services": ["legal advice", "law firm", "court"],
    "high_capital": ["life savings", "all my money", "borrow", "debt"],
}


def _match_rules(text: str) -> list[tuple[RouteRule, int]]:
    lowered = text.lower()
    scored = []
    for rule in RULES:
        hits = sum(1 for kw in rule.keywords if kw in lowered)
        if hits:
            scored.append((rule, hits))
    # Highest risk wins the primary slot; keyword hits break ties.
    scored.sort(key=lambda pair: (RISK_ORDER[pair[0].risk_level], pair[1]), reverse=True)
    return scored


def _domain_escalations(text: str) -> list[str]:
    lowered = text.lower()
    return [
        domain
        for domain, keywords in HIGH_RISK_DOMAINS.items()
        if any(kw in lowered for kw in keywords)
    ]


def _founder_fit_note(text: str, engine: Engine | None) -> tuple[str | None, list[str]]:
    if engine is None:
        return None, []
    from app.api.venture import list_memories
    from app.venture.founder import get_founder_profile

    warnings: list[str] = []
    notes: list[str] = []
    profile = get_founder_profile(engine)
    lowered = text.lower()

    if profile["budget_range"]:
        notes.append(f"budget range on file: {profile['budget_range']}")
    if profile["risk_tolerance"]:
        notes.append(f"risk tolerance: {profile['risk_tolerance']}")
    for key, label in (("distracting_ideas", "matches your declared distractions"),
                       ("avoid", "matches your avoid-list")):
        for word in profile[key].replace(",", " ").split():
            if len(word) > 4 and word.lower() in lowered:
                warnings.append(f"'{word}' {label} ({key}).")
                break

    # The anti-distraction check: has a similar idea already been rejected?
    for memory in list_memories(engine, category="rejected_idea", limit=25):
        title_words = {w.lower() for w in memory["title"].split() if len(w) > 4}
        request_words = {w.lower().strip(".,!?") for w in text.split() if len(w) > 4}
        if len(title_words & request_words) >= 2:
            warnings.append(
                f"A similar idea was already rejected: {memory['title']!r} "
                f"(memory #{memory['id']}). Read it before re-litigating."
            )
            break

    return ("; ".join(notes) if notes else None), warnings


def route(text: str, engine: Engine | None = None) -> RouteDecision:
    """Route a free-text request. Deterministic; safe to call anywhere."""
    text = (text or "").strip()
    matches = _match_rules(text)
    escalations = _domain_escalations(text)

    if not matches:
        decision = RouteDecision(
            category="general",
            primary_agent="ceo",
            supporting_agents=[],
            workflow=["ceo_chat"],
            risk_level="low",
            reason="No venture routing rule matched; the operations CEO handles it "
                   "as a normal chat request.",
            required_inputs=["the request itself"],
            expected_output="CEO-synthesized answer from the specialist roster",
        )
    else:
        top_rule = matches[0][0]
        supporting: list[str] = []
        for rule, _ in matches:
            for agent in [rule.primary_agent, *rule.supporting_agents]:
                if agent != top_rule.primary_agent and agent not in supporting:
                    supporting.append(agent)
        decision = RouteDecision(
            category=top_rule.category,
            primary_agent=top_rule.primary_agent,
            supporting_agents=supporting,
            workflow=list(top_rule.workflow),
            risk_level=top_rule.risk_level,
            reason=top_rule.reason,
            required_inputs=list(top_rule.required_inputs),
            expected_output=top_rule.expected_output,
            matched_categories=[rule.category for rule, _ in matches],
        )

    if escalations:
        decision.risk_level = "high"
        if "risk" not in (decision.primary_agent, *decision.supporting_agents):
            decision.supporting_agents.append("risk")
        decision.reason += (
            f" Escalated to HIGH risk: regulated/trust-critical domain detected "
            f"({', '.join(escalations)}) — the Risk Officer joins and a debate is "
            "recommended before commitment."
        )
        if "debate" not in decision.workflow:
            decision.workflow.append("debate")

    note, warnings = _founder_fit_note(text, engine)
    decision.founder_fit_note = note
    decision.warnings.extend(warnings)
    return decision
