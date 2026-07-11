"""Venture layer: the deterministic prompt router."""
from __future__ import annotations

import shutil

from app.api.venture import save_memory_record
from app.db import make_engine
from app.venture.founder import set_founder_profile
from app.venture.router import RULES, route


def test_rule_table_covers_the_15_categories():
    assert len(RULES) == 15
    assert {r.risk_level for r in RULES} <= {"low", "medium", "high"}
    for rule in RULES:
        assert rule.keywords and rule.reason and rule.required_inputs
        assert rule.workflow, rule.category


def test_doctor_example_escalates_to_high_risk_with_risk_officer():
    decision = route("I want to launch an AI tool for doctors.")
    assert decision.category == "business_idea_validation"
    assert decision.primary_agent == "ceo"
    assert decision.risk_level == "high"  # healthcare domain modifier
    assert "risk" in decision.supporting_agents
    assert "debate" in decision.workflow
    assert "healthcare" in decision.reason


def test_plain_validation_request_stays_medium():
    decision = route("Should I start a business selling productized Notion setups?")
    assert decision.category == "business_idea_validation"
    assert decision.risk_level == "medium"


def test_category_routing_samples():
    assert route("Write a cold email for my offer").primary_agent == "sales"
    assert route("What's our runway and burn?").primary_agent == "cfo"
    assert route("Do I need a license or legal review for this?").primary_agent == "risk"
    assert route("Which tech stack and database should I use?").primary_agent == "venture_cto"
    assert route("Research the competitors in this market").primary_agent == "researcher"
    pivot = route("Growth stalled — should we pivot to a new direction?")
    assert pivot.category == "pivot"
    assert pivot.risk_level == "high"


def test_multi_match_merges_supporting_agents():
    decision = route("Validate this idea and draft the marketing plan and sales copy")
    assert decision.matched_categories[0] == decision.category
    assert len(decision.matched_categories) >= 2
    merged = set(decision.supporting_agents)
    assert decision.primary_agent not in merged


def test_no_match_defaults_to_ceo_low_risk():
    decision = route("hello there")
    assert decision.category == "general"
    assert decision.primary_agent == "ceo"
    assert decision.risk_level == "low"


def test_founder_profile_and_rejected_ideas_shape_the_note(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    engine = make_engine(db_copy)

    set_founder_profile(
        engine,
        {"budget_range": "₹50,000 total", "risk_tolerance": "medium",
         "distracting_ideas": "crypto tools"},
    )
    save_memory_record(
        engine,
        category="rejected_idea",
        title="Generic resume builder tool — NO-GO",
        content="Rejected for zero distribution.",
        source_agent="scorer",
    )

    decision = route("I want to build a crypto trading tool", engine)
    assert decision.founder_fit_note and "₹50,000" in decision.founder_fit_note
    assert any("crypto" in w for w in decision.warnings)
    assert decision.risk_level == "high"  # finance_regulated domain

    rejected = route("should I build a resume builder tool for engineers", engine)
    assert any("already rejected" in w for w in rejected.warnings)
