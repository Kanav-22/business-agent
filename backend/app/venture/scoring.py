"""Idea Scoring Engine — the deterministic half of idea scoring.

The scorer agent *proposes* per-category scores with rationales; this module
validates them, computes the total, and derives the verdict from fixed, strict
thresholds. Agents cannot inflate a verdict: the math is code, not vibes.

Verdict rules (strict on purpose — see docs/AUDIT.md):
- GO          avg ≥ 7.5 AND no category ≤ 3 AND market_demand, founder_fit and
              speed_to_revenue all ≥ 6. Rare by design.
- NO_GO       avg < 5.5 OR any category ≤ 2 OR market_demand ≤ 3.
- TEST_FIRST  everything else — the default outcome for promising-but-unproven.
"""
from __future__ import annotations

from dataclasses import dataclass

# (key, what a 10 means) — every category is scored 1-10 where 10 is GOOD, so
# the "risk-like" categories are phrased inversely (10 = cheap/safe/simple).
CATEGORIES: list[tuple[str, str]] = [
    ("market_demand", "10 = urgent, frequent, budgeted pain with evidence of people paying today"),
    ("ease_of_mvp", "10 = a useful v1 ships in days with existing skills/tools"),
    ("speed_to_revenue", "10 = first payment plausible within 2 weeks"),
    ("competition_level", "10 = weak/fragmented competition you can outflank; 1 = entrenched giants"),
    ("founder_fit", "10 = matches the founder profile's skills, assets and interests exactly"),
    ("distribution_advantage", "10 = existing audience/channel/partnerships reach buyers now"),
    ("technical_complexity", "10 = trivially simple to build and operate; 1 = research-grade hard"),
    ("legal_regulatory_risk", "10 = no meaningful regulatory surface; 1 = licensed/regulated activity"),
    ("capital_required", "10 = near-zero cash needed before revenue; 1 = heavy upfront capital"),
    ("scalability", "10 = marginal cost per additional customer near zero"),
    ("profit_margin", "10 = software-like margins (>80%); 1 = thin resale margins"),
    ("defensibility", "10 = compounding moat (data, network, switching costs); 1 = clonable in a weekend"),
    ("time_to_first_customer", "10 = a named first customer is reachable this week"),
    ("risk_adjusted_upside", "10 = large upside even after discounting the failure modes"),
]

CATEGORY_KEYS = [key for key, _ in CATEGORIES]

# Verdict thresholds — change them here, nowhere else.
GO_MIN_AVG = 7.5
GO_MIN_ANY = 4  # a GO idea may not have any category at 3 or below
GO_CRITICAL = ("market_demand", "founder_fit", "speed_to_revenue")
GO_CRITICAL_MIN = 6
NO_GO_MAX_AVG = 5.5
NO_GO_ANY_AT_OR_BELOW = 2
NO_GO_DEMAND_AT_OR_BELOW = 3

VERDICT_LABELS = {"go": "GO", "no_go": "NO-GO", "test_first": "TEST FIRST"}


class ScoringError(ValueError):
    """Invalid proposed scores (missing category, out of range, wrong type)."""


@dataclass
class ScoreResult:
    scores: dict[str, int]
    total: float  # average across the 14 categories, 1 decimal
    verdict: str  # 'go' | 'no_go' | 'test_first'

    @property
    def verdict_label(self) -> str:
        return VERDICT_LABELS[self.verdict]


def validate_scores(raw: dict) -> dict[str, int]:
    """Every category present, integer, 1-10. Extra keys are rejected so typos
    can't silently drop a category."""
    if not isinstance(raw, dict):
        raise ScoringError("scores must be an object of {category: 1-10}.")
    unknown = sorted(set(raw) - set(CATEGORY_KEYS))
    if unknown:
        raise ScoringError(f"unknown score categories: {', '.join(unknown)}.")
    missing = [k for k in CATEGORY_KEYS if k not in raw]
    if missing:
        raise ScoringError(f"missing score categories: {', '.join(missing)}.")
    cleaned: dict[str, int] = {}
    for key in CATEGORY_KEYS:
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ScoringError(f"{key} must be an integer 1-10.")
        if not 1 <= value <= 10:
            raise ScoringError(f"{key} must be between 1 and 10, got {value}.")
        cleaned[key] = value
    return cleaned


def score(raw_scores: dict) -> ScoreResult:
    scores = validate_scores(raw_scores)
    total = round(sum(scores.values()) / len(scores), 1)
    lowest = min(scores.values())

    if (
        total < NO_GO_MAX_AVG
        or lowest <= NO_GO_ANY_AT_OR_BELOW
        or scores["market_demand"] <= NO_GO_DEMAND_AT_OR_BELOW
    ):
        verdict = "no_go"
    elif (
        total >= GO_MIN_AVG
        and lowest >= GO_MIN_ANY
        and all(scores[k] >= GO_CRITICAL_MIN for k in GO_CRITICAL)
    ):
        verdict = "go"
    else:
        verdict = "test_first"
    return ScoreResult(scores=scores, total=total, verdict=verdict)


def explain_verdict(result: ScoreResult) -> str:
    """One sentence saying which rule fired — keeps the engine auditable."""
    s = result.scores
    if result.verdict == "no_go":
        reasons = []
        if result.total < NO_GO_MAX_AVG:
            reasons.append(f"average {result.total} is below {NO_GO_MAX_AVG}")
        floor = min(s, key=s.get)
        if s[floor] <= NO_GO_ANY_AT_OR_BELOW:
            reasons.append(f"{floor} is critically low ({s[floor]})")
        if s["market_demand"] <= NO_GO_DEMAND_AT_OR_BELOW:
            reasons.append(f"market_demand is {s['market_demand']}")
        return "NO-GO because " + " and ".join(reasons) + "."
    if result.verdict == "go":
        return (
            f"GO: average {result.total} ≥ {GO_MIN_AVG}, no category below "
            f"{GO_MIN_ANY}, and demand/fit/speed all ≥ {GO_CRITICAL_MIN}."
        )
    blockers = []
    if result.total < GO_MIN_AVG:
        blockers.append(f"average {result.total} < {GO_MIN_AVG}")
    weak_critical = [k for k in GO_CRITICAL if s[k] < GO_CRITICAL_MIN]
    if weak_critical:
        blockers.append(f"{', '.join(weak_critical)} below {GO_CRITICAL_MIN}")
    if min(s.values()) < GO_MIN_ANY:
        floor = min(s, key=s.get)
        blockers.append(f"{floor} at {s[floor]}")
    return "TEST FIRST: not a NO-GO, but blocked from GO by " + "; ".join(blockers) + "."


def render_scoreboard(scores: dict[str, int], rationales: dict[str, str]) -> str:
    """Markdown table of category / score / rationale, in canonical order."""
    lines = ["| Category | Score | Rationale |", "|---|---|---|"]
    for key in CATEGORY_KEYS:
        rationale = (rationales.get(key) or "").strip().replace("|", "/")
        lines.append(f"| {key} | {scores[key]}/10 | {rationale} |")
    return "\n".join(lines)
