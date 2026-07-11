"""Venture layer: the deterministic idea-scoring engine and score_idea tool."""
from __future__ import annotations

import asyncio
import shutil

import pytest

from app.api.venture import get_idea, list_ideas, list_memories
from app.db import make_engine
from app.tools.base import ToolError
from app.tools.score_idea import make_score_idea_tool
from app.venture.scoring import (
    CATEGORY_KEYS,
    ScoringError,
    explain_verdict,
    score,
    validate_scores,
)


def flat(value: int) -> dict[str, int]:
    return {key: value for key in CATEGORY_KEYS}


# ------------------------------------------------------------ engine verdicts


def test_go_requires_high_average_and_no_weak_category():
    assert score(flat(8)).verdict == "go"
    # One category at 3 blocks GO even with a high average.
    scores = flat(9)
    scores["defensibility"] = 3
    assert score(scores).verdict == "test_first"
    # Critical categories must clear 6.
    scores = flat(8)
    scores["founder_fit"] = 5
    assert score(scores).verdict == "test_first"


def test_no_go_rules():
    assert score(flat(5)).verdict == "no_go"  # avg 5.0 < 5.5
    scores = flat(7)
    scores["legal_regulatory_risk"] = 2  # any category <= 2
    assert score(scores).verdict == "no_go"
    scores = flat(8)
    scores["market_demand"] = 3  # demand floor
    assert score(scores).verdict == "no_go"


def test_test_first_is_the_middle_ground():
    result = score(flat(6))
    assert result.verdict == "test_first"
    assert result.total == 6.0
    assert "TEST FIRST" in explain_verdict(result)


def test_validation_rejects_bad_scores():
    with pytest.raises(ScoringError, match="missing"):
        validate_scores({"market_demand": 5})
    with pytest.raises(ScoringError, match="unknown"):
        validate_scores({**flat(5), "hype": 10})
    with pytest.raises(ScoringError, match="between 1 and 10"):
        validate_scores({**flat(5), "market_demand": 11})
    with pytest.raises(ScoringError, match="integer"):
        validate_scores({**flat(5), "market_demand": 7.5})
    with pytest.raises(ScoringError, match="integer"):
        validate_scores({**flat(5), "market_demand": True})


# ----------------------------------------------------------- score_idea tool


class Ctx:
    agent = "scorer"
    run_id = "test"
    depth = 0
    budget = None
    on_event = None
    extra = None


def tool_input(**overrides) -> dict:
    base = {
        "title": "AI booking for dermatology clinics",
        "description": "Automated WhatsApp booking for solo clinics.",
        "scores": flat(6),
        "rationales": {key: "test rationale" for key in CATEGORY_KEYS},
        "best_version": "Pre-sold pilot for 3 clinics.",
        "worst_risk": "Demand assumed.",
        "validation_test": "Pre-sell in one week, ~zero cost.",
        "next_actions": ["List 100 clinics", "Book 5 calls", "Pre-sell a pilot"],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def writable_engine(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    return make_engine(db_copy)


def test_score_idea_persists_idea_and_memory(writable_engine):
    tool = make_score_idea_tool(writable_engine)
    result = asyncio.run(tool.handler(tool_input(), Ctx()))
    assert "TEST FIRST" in result and "deterministic" in result

    ideas = list_ideas(writable_engine)
    assert len(ideas) == 1
    idea = get_idea(writable_engine, ideas[0]["id"])
    assert idea["verdict"] == "test_first"
    assert idea["total_score"] == 6.0
    assert idea["scores"]["market_demand"]["score"] == 6
    assert "- List 100 clinics" in idea["next_actions"]

    memories = list_memories(writable_engine, category="business_idea")
    assert len(memories) == 1
    assert "TEST FIRST" in memories[0]["title"]


def test_score_idea_no_go_saves_rejected_idea_memory(writable_engine):
    tool = make_score_idea_tool(writable_engine)
    asyncio.run(tool.handler(tool_input(scores=flat(4)), Ctx()))
    assert list_memories(writable_engine, category="rejected_idea")
    assert not list_memories(writable_engine, category="business_idea")


def test_score_idea_rejects_invalid_input(writable_engine):
    tool = make_score_idea_tool(writable_engine)
    with pytest.raises(ToolError, match="title"):
        asyncio.run(tool.handler(tool_input(title=""), Ctx()))
    with pytest.raises(ToolError, match="exactly 3"):
        asyncio.run(tool.handler(tool_input(next_actions=["only one"]), Ctx()))
    with pytest.raises(ToolError, match="missing rationales"):
        asyncio.run(tool.handler(tool_input(rationales={}), Ctx()))
    with pytest.raises(ToolError, match="between 1 and 10"):
        asyncio.run(
            tool.handler(tool_input(scores={**flat(6), "market_demand": 0}), Ctx())
        )
    # Nothing was persisted by the failed calls.
    assert list_ideas(writable_engine) == []
