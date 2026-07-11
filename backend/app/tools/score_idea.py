"""score_idea — the Idea Scorer's only output path.

The agent proposes 14 category scores (1-10) with rationales plus the
qualitative fields; deterministic code (app/venture/scoring.py) validates the
scores, computes the total and the verdict from fixed strict thresholds, and
persists the idea + a memory record. The agent cannot choose the verdict."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.engine import Engine

from app.api.venture import save_idea, save_memory_record
from app.tools.base import Tool, ToolError
from app.venture.scoring import (
    CATEGORIES,
    CATEGORY_KEYS,
    ScoringError,
    explain_verdict,
    score,
)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext

MAX_TEXT = 2000
MAX_RATIONALE = 300

SCORE_IDEA_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short idea name (max 200 chars)."},
        "description": {"type": "string", "description": "The idea as stated/refined."},
        "scores": {
            "type": "object",
            "description": "Integer 1-10 per category. Score STRICTLY: " + "; ".join(
                f"{key}: {meaning}" for key, meaning in CATEGORIES
            ),
            "properties": {
                key: {"type": "integer", "minimum": 1, "maximum": 10} for key in CATEGORY_KEYS
            },
            "required": CATEGORY_KEYS,
        },
        "rationales": {
            "type": "object",
            "description": "One-sentence justification per category (same keys as scores).",
            "properties": {key: {"type": "string"} for key in CATEGORY_KEYS},
            "required": CATEGORY_KEYS,
        },
        "best_version": {
            "type": "string",
            "description": "The strongest reshaping of this idea (niche, angle, scope).",
        },
        "worst_risk": {"type": "string", "description": "The single worst risk."},
        "validation_test": {
            "type": "string",
            "description": "The cheapest test that would validate/kill the idea (cost + time).",
        },
        "next_actions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
            "description": "Exactly 3 concrete next actions.",
        },
    },
    "required": [
        "title",
        "description",
        "scores",
        "rationales",
        "best_version",
        "worst_risk",
        "validation_test",
        "next_actions",
    ],
}


def _clean_text(tool_input: dict, field: str, *, required: bool = True) -> str:
    value = (tool_input.get(field) or "").strip()
    if required and not value:
        raise ToolError(f"{field} is required.")
    if len(value) > MAX_TEXT:
        raise ToolError(f"{field} exceeds {MAX_TEXT} characters.")
    return value


def make_score_idea_tool(engine: Engine) -> Tool:
    async def handler(tool_input: dict, ctx: "ToolContext") -> str:
        title = _clean_text(tool_input, "title")
        if len(title) > 200:
            raise ToolError("title must be at most 200 characters.")
        description = _clean_text(tool_input, "description")
        best_version = _clean_text(tool_input, "best_version")
        worst_risk = _clean_text(tool_input, "worst_risk")
        validation_test = _clean_text(tool_input, "validation_test")

        next_actions = tool_input.get("next_actions")
        if not isinstance(next_actions, list) or len(next_actions) != 3:
            raise ToolError("next_actions must be an array of exactly 3 strings.")
        actions = []
        for i, raw in enumerate(next_actions):
            action = str(raw or "").strip()
            if not action:
                raise ToolError(f"next_actions[{i}] is empty.")
            actions.append(action[:300])

        rationales_raw = tool_input.get("rationales")
        if not isinstance(rationales_raw, dict):
            raise ToolError("rationales must be an object with the same keys as scores.")
        rationales = {
            key: str(rationales_raw.get(key) or "").strip()[:MAX_RATIONALE]
            for key in CATEGORY_KEYS
        }
        missing = [k for k in CATEGORY_KEYS if not rationales[k]]
        if missing:
            raise ToolError(f"missing rationales for: {', '.join(missing)}.")

        try:
            result = score(tool_input.get("scores") or {})
        except ScoringError as exc:
            raise ToolError(str(exc))

        idea_id = save_idea(
            engine,
            title=title,
            description=description,
            scores=result.scores,
            rationales=rationales,
            total_score=result.total,
            verdict=result.verdict,
            best_version=best_version,
            worst_risk=worst_risk,
            validation_test=validation_test,
            next_actions=actions,
        )
        memory_category = "rejected_idea" if result.verdict == "no_go" else "business_idea"
        save_memory_record(
            engine,
            category=memory_category,
            title=f"{title} — {result.verdict_label} ({result.total}/10)",
            content=(
                f"{explain_verdict(result)} Worst risk: {worst_risk} "
                f"Cheapest validation: {validation_test} Idea record: #{idea_id}."
            ),
            source_agent=ctx.agent,
            related_idea=title[:80],
        )
        return (
            f"Idea #{idea_id} scored: {result.total}/10 → {result.verdict_label}. "
            f"{explain_verdict(result)} The verdict was computed by the deterministic "
            "engine and cannot be overridden."
        )

    return Tool(
        name="score_idea",
        description=(
            "Submit strict 1-10 scores for a business idea across the 14 fixed "
            "categories, with rationales and the qualitative fields. Deterministic "
            "code computes the total and the Go/No-Go/Test-First verdict from fixed "
            "thresholds and persists the result — you propose scores, never the "
            "verdict. Score strictly; excitement is not evidence."
        ),
        input_schema=SCORE_IDEA_SCHEMA,
        handler=handler,
    )
