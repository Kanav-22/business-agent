"""Deterministic structural scoring for agent evaluation cases.

Each case assigns weights to required output elements. The scorer converts the
matched-weight share to a 0-10 base score, subtracts case-specific and generic
bad-sign penalties, subtracts 1.5 when the output lacks the required number of
numeric anchors, then clamps and rounds to one decimal. No model judges another
model: the same text and case always produce the same score.
"""
from __future__ import annotations

import re

GENERIC_BAD_SIGNS = [
    {
        "name": "hype cliché",
        "pattern": r"game-?chang|revolutioniz|cutting[- ]edge|unlock (growth|potential)|synerg",
        "penalty": 1.0,
    },
    {
        "name": "hedging non-answer",
        "pattern": r"it depends|there are many factors|only time will tell",
        "penalty": 1.0,
    },
]

_FLAGS = re.IGNORECASE | re.DOTALL
_NUMBER_PATTERN = re.compile(r"\d[\d,.]*%?|₹|\$")


def _criterion(
    name: str,
    kind: str,
    hit: bool,
    weight_or_penalty: float,
) -> dict:
    return {
        "name": name,
        "kind": kind,
        "hit": hit,
        "weight_or_penalty": float(weight_or_penalty),
    }


def score_output(case: dict, output: str) -> dict:
    """Score one output against a validated case's structural rubric."""
    text = output or ""
    is_blank = not text.strip()
    expected = case["expected_elements"]
    bad_signs = [*case.get("bad_signs", []), *GENERIC_BAD_SIGNS]
    criteria: list[dict] = []

    matched_weight = 0.0
    total_weight = sum(float(item["weight"]) for item in expected)
    for item in expected:
        hit = False if is_blank else bool(re.search(item["pattern"], text, flags=_FLAGS))
        weight = float(item["weight"])
        if hit:
            matched_weight += weight
        criteria.append(_criterion(item["name"], "expected", hit, weight))

    penalties = 0.0
    for item in bad_signs:
        hit = False if is_blank else bool(re.search(item["pattern"], text, flags=_FLAGS))
        penalty = float(item["penalty"])
        if hit:
            penalties += penalty
        criteria.append(_criterion(item["name"], "bad_sign", hit, penalty))

    min_numbers = int(case.get("min_numbers", 0))
    number_count = len(_NUMBER_PATTERN.findall(text))
    numbers_missing = number_count < min_numbers
    if numbers_missing:
        penalties += 1.5
        criteria.append(
            _criterion(
                f"at least {min_numbers} numeric anchors (found {number_count})",
                "numbers",
                False,
                1.5,
            )
        )

    if is_blank:
        score = 0.0
    else:
        base = 10.0 * matched_weight / total_weight if total_weight else 0.0
        score = round(max(0.0, min(10.0, base - penalties)), 1)

    passed = score >= float(case["pass_score"])
    return {
        "score": score,
        "passed": passed,
        "criteria": criteria,
        "suggestions": [] if passed else list(case["improvement_suggestions"]),
    }
