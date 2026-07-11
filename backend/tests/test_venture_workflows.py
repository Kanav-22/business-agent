"""V3 venture workflows: deterministic orchestration, persistence, and API."""
from __future__ import annotations

import asyncio
import shutil
import threading
import time
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentResult
from app.agents.service import AgentService
from app.api.reports import get_report
from app.api.venture import (
    get_idea,
    list_ideas,
    list_memories,
    save_idea,
)
from app.db import make_engine
from app.main import create_app
from app.venture.scoring import CATEGORY_KEYS
from app.venture.workflows import (
    VENTURE_WORKFLOWS,
    run_customer_interviews,
    run_debate,
    run_failure_simulation,
    run_idea_score,
)
from tests.fake_anthropic import FakeClient, response, text_block, tool_use_block


@pytest.fixture()
def writable_settings(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    return settings


@pytest.fixture()
def writable_engine(writable_settings):
    return make_engine(writable_settings.db_path)


def make_service(settings, routes) -> tuple[AgentService, FakeClient]:
    fake = FakeClient(routes)
    return AgentService(settings, client_factory=lambda: fake), fake


def score_input() -> dict:
    return {
        "title": "AI booking for dermatology clinics",
        "description": "Automated booking for solo dermatology clinics.",
        "scores": {key: 6 for key in CATEGORY_KEYS},
        "rationales": {
            key: "Evidence is still unvalidated." for key in CATEGORY_KEYS
        },
        "best_version": "Pre-sold pilot for three clinics.",
        "worst_risk": "Demand is assumed.",
        "validation_test": "Pre-sell in one week at near-zero cost.",
        "next_actions": [
            "List 100 clinics",
            "Book five calls",
            "Pre-sell one pilot",
        ],
    }


def save_test_idea(engine, title: str) -> int:
    return save_idea(
        engine,
        title=title,
        description=f"Description for {title}.",
        scores={key: 6 for key in CATEGORY_KEYS},
        rationales={key: f"Rationale for {title}." for key in CATEGORY_KEYS},
        total_score=6.0,
        verdict="test_first",
        best_version=f"Best version of {title}.",
        worst_risk=f"Worst risk for {title}.",
        validation_test=f"Validation test for {title}.",
        next_actions=["One", "Two", "Three"],
    )


async def test_run_debate_saves_report_and_decision_memory(
    writable_settings, writable_engine
):
    topic = "Launch an AI tool for doctors"
    outputs = {
        "cfo": "CFO objection: cash arrives after delivery.",
        "cmo": "CMO objection: demand has not been proven.",
        "cto": "CTO objection: the integration is untested.",
        "coo": "COO objection: founder capacity is missing.",
        "risk": "Risk objection: health claims need review.",
    }
    routes = {
        "venture strategist": [
            response([text_block("Proposal with Assumption 1 and Assumption 2.")]),
            response([text_block("Revised plan with an owner and deadline.")]),
        ],
        "financial skeptic": [response([text_block(outputs["cfo"])])],
        "demand skeptic": [response([text_block(outputs["cmo"])])],
        "feasibility skeptic": [response([text_block(outputs["cto"])])],
        "COO agent": [response([text_block(outputs["coo"])])],
        "Risk Officer agent": [response([text_block(outputs["risk"])])],
        "Researcher agent": [response([text_block("Assumption check result.")])],
    }
    service, fake = make_service(writable_settings, routes)

    report_id = await run_debate(service, writable_engine, topic)

    report = get_report(writable_engine, report_id)
    assert report["kind"] == "debate"
    assert report["agent"] == "venture_ceo"
    content = report["content"]
    headings = [
        "## Original proposal",
        "## Agent objections",
        "## Researcher — assumption check",
        "## Counterarguments & revision",
    ]
    assert [content.index(heading) for heading in headings] == sorted(
        content.index(heading) for heading in headings
    )
    for subheading in ("CFO", "CMO", "CTO", "COO", "Risk Officer"):
        assert f"### {subheading}" in content
    assert outputs["cfo"] in content

    memories = list_memories(writable_engine, category="decision")
    memory = next(m for m in memories if m["related_idea"] == topic[:80])
    assert memory["source_agent"] == "venture_ceo"
    assert f"Full report: #{report_id}." in memory["content"]

    ceo_calls = [
        call for call in fake.calls if "venture strategist" in call["system"]
    ]
    assert len(ceo_calls) == 2
    revision_task = ceo_calls[1]["messages"][-1]["content"]
    assert "Revise" in revision_task and "objections" in revision_task
    for output in outputs.values():
        assert output in revision_task
    assert all(
        call["messages"][0]["content"].startswith(f"TOPIC: {topic}\n")
        for call in fake.calls
    )


async def test_debate_runs_all_five_critics_in_parallel_with_one_budget(
    writable_settings, writable_engine
):
    routes = {
        "venture strategist": [
            response([text_block("Proposal with numbered assumptions.")]),
            response([text_block("Revised plan with a decision.")]),
        ],
        "Researcher agent": [response([text_block("Assumptions checked.")])],
    }
    service, _ = make_service(writable_settings, routes)
    critic_names = {"venture_cfo", "venture_cmo", "venture_cto", "coo", "risk"}
    started: set[str] = set()
    budget_ids: set[int] = set()
    all_started = asyncio.Event()

    def make_critic_run(name):
        async def critic_run(task, *, on_event, budget):
            started.add(name)
            budget_ids.add(id(budget))
            if started == critic_names:
                all_started.set()
            await asyncio.wait_for(all_started.wait(), timeout=1)
            return AgentResult(
                run_id=name,
                agent=name,
                output=f"{name} objection",
            )

        return critic_run

    for name in critic_names:
        service.venture_team[name].run = make_critic_run(name)

    report_id = await run_debate(service, writable_engine, "Parallel debate")

    assert started == critic_names
    assert len(budget_ids) == 1
    assert "unavailable" not in get_report(writable_engine, report_id)["content"]


async def test_failure_simulation_saves_report_and_risk_memory(
    writable_settings, writable_engine
):
    topic = "Launch an AI tool for doctors"
    routes = {
        "Red Team agent": [response([text_block("Fatal failure mode.")])],
        "Risk Officer agent": [response([text_block("Regulatory exposure.")])],
    }
    service, fake = make_service(writable_settings, routes)

    report_id = await run_failure_simulation(service, writable_engine, topic)

    report = get_report(writable_engine, report_id)
    assert report["kind"] == "failure_sim"
    assert report["agent"] == "red_team"
    assert "## Red team — failure modes" in report["content"]
    assert "## Risk officer — exposure" in report["content"]
    assert "## How to use this" in report["content"]
    assert "Fatal failure mode." in report["content"]
    assert "Regulatory exposure." in report["content"]

    memory = list_memories(writable_engine, category="risk")[0]
    assert memory["source_agent"] == "red_team"
    assert f"Full report: #{report_id}." in memory["content"]

    for call in fake.calls:
        task = call["messages"][0]["content"]
        for required in (
            "7 days",
            "30 days",
            "90 days",
            "1 year",
            "early warning signs",
            "probability",
            "prevention plan",
            "recovery plan",
            "agent responsible",
        ):
            assert required in task


async def test_failure_simulation_runs_agents_in_parallel_with_one_budget(
    writable_settings, writable_engine
):
    service, _ = make_service(writable_settings, {})
    started: set[str] = set()
    budget_ids: set[int] = set()
    both_started = asyncio.Event()

    async def barrier_run(name, task, *, on_event, budget):
        started.add(name)
        budget_ids.add(id(budget))
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=1)
        return AgentResult(run_id=name, agent=name, output=f"{name} completed")

    async def red_run(task, *, on_event, budget):
        return await barrier_run("red_team", task, on_event=on_event, budget=budget)

    async def risk_run(task, *, on_event, budget):
        return await barrier_run("risk", task, on_event=on_event, budget=budget)

    service.venture_team["red_team"].run = red_run
    service.venture_team["risk"].run = risk_run

    report_id = await run_failure_simulation(
        service, writable_engine, "Parallel workflow"
    )

    assert started == {"red_team", "risk"}
    assert len(budget_ids) == 1
    assert "unavailable" not in get_report(writable_engine, report_id)["content"]


async def test_customer_interviews_adds_disclaimer_and_saves_synthesis(
    writable_settings, writable_engine
):
    output = (
        "Persona prelude that must not enter memory.\n\n"
        "Synthesis: strongest segment is owner-operated clinics."
    )
    service, _ = make_service(
        writable_settings,
        {"Interviewer agent": [response([text_block(output)])]},
    )

    report_id = await run_customer_interviews(
        service, writable_engine, "AI tool for doctors"
    )

    report = get_report(writable_engine, report_id)
    first_line = report["content"].splitlines()[0]
    assert first_line.startswith("**") and first_line.endswith("**")
    assert "synthetic" in first_line.lower()
    assert "real" in first_line.lower()
    assert "validate" in first_line.lower()
    assert output in report["content"]

    memory = list_memories(writable_engine, category="customer_research")[0]
    assert memory["source_agent"] == "interviewer"
    assert memory["content"].startswith("Synthesis")
    assert "Persona prelude" not in memory["content"]


async def test_idea_score_persists_idea_and_scoreboard_report(
    writable_settings, writable_engine
):
    routes = {
        "Idea Scorer agent": [
            response(
                [tool_use_block("score_1", "score_idea", score_input())],
                stop_reason="tool_use",
            ),
            response(
                [text_block("Verdict: TEST FIRST\nFirst action: list clinics.")]
            ),
        ]
    }
    service, _ = make_service(writable_settings, routes)

    report_id = await run_idea_score(
        service, writable_engine, "AI booking for dermatology clinics"
    )

    ideas = list_ideas(writable_engine)
    assert len(ideas) == 1
    idea = get_idea(writable_engine, ideas[0]["id"])
    assert idea["verdict"] == "test_first"
    assert idea["total_score"] == 6.0

    report = get_report(writable_engine, report_id)
    assert report["kind"] == "idea_score"
    assert report["agent"] == "scorer"
    for expected in (
        "TEST FIRST",
        "| Category | Score | Rationale |",
        "| market_demand | 6/10 | Evidence is still unvalidated. |",
        "Pre-sold pilot for three clinics.",
        "Demand is assumed.",
        "Pre-sell in one week at near-zero cost.",
        "- List 100 clinics",
    ):
        assert expected in report["content"]
    assert list_memories(writable_engine, category="business_idea")


async def test_agent_error_is_embedded_and_report_still_saved(
    writable_settings, writable_engine
):
    service, _ = make_service(
        writable_settings,
        {"Red Team agent": [response([text_block("Red team completed.")])]},
    )
    risk_run = AsyncMock(
        return_value=AgentResult(
            run_id="failed",
            agent="risk",
            output="",
            error="model_error",
        )
    )
    service.venture_team["risk"].run = risk_run

    report_id = await run_failure_simulation(
        service, writable_engine, "AI tool for doctors"
    )

    report = get_report(writable_engine, report_id)
    assert "unavailable" in report["content"]
    assert "model_error" in report["content"]
    risk_run.assert_awaited_once()


async def test_missing_agent_is_embedded_and_report_still_saved(
    writable_settings, writable_engine
):
    service, _ = make_service(
        writable_settings,
        {"Red Team agent": [response([text_block("Red team completed.")])]},
    )
    service.venture_team.pop("risk")

    report_id = await run_failure_simulation(
        service, writable_engine, "AI tool for doctors"
    )

    report = get_report(writable_engine, report_id)
    assert "[Risk unavailable: KeyError:" in report["content"]


async def test_idea_score_without_new_tool_call_does_not_reuse_existing_idea(
    writable_settings, writable_engine
):
    existing_id = save_test_idea(writable_engine, "Existing idea")
    service, _ = make_service(
        writable_settings,
        {"Idea Scorer agent": [response([text_block("I did not use the tool.")])]},
    )

    report_id = await run_idea_score(service, writable_engine, "A new idea")

    assert list_ideas(writable_engine, limit=1)[0]["id"] == existing_id
    report = get_report(writable_engine, report_id)
    assert "No idea was scored" in report["content"]
    assert "Best version of Existing idea" not in report["content"]


async def test_idea_score_uses_the_id_emitted_by_its_own_tool_run(
    writable_settings, writable_engine
):
    service, _ = make_service(writable_settings, {})

    async def interleaved_run(task, *, on_event, budget):
        own_id = save_test_idea(writable_engine, "Workflow-owned idea")
        await on_event(
            {
                "type": "tool_result",
                "tool": "score_idea",
                "is_error": False,
                "output": f"Idea #{own_id} scored: 6.0/10.",
            }
        )
        save_test_idea(writable_engine, "Concurrent idea")
        return AgentResult(
            run_id="interleaved",
            agent="scorer",
            output="Workflow scorer closing text.",
        )

    service.venture_team["scorer"].run = interleaved_run

    report_id = await run_idea_score(service, writable_engine, "Score this")

    assert list_ideas(writable_engine, limit=1)[0]["title"] == "Concurrent idea"
    report = get_report(writable_engine, report_id)
    assert report["title"] == "Idea score: Workflow-owned idea"
    assert "Best version of Workflow-owned idea" in report["content"]
    assert "Best version of Concurrent idea" not in report["content"]


def test_venture_workflow_api_contract(writable_settings, monkeypatch):
    service, _ = make_service(writable_settings, [])
    calls = []
    called = threading.Event()

    async def fake_run(passed_service, engine, topic, *, on_event=None):
        calls.append((passed_service, engine, topic, on_event))
        called.set()
        return 123

    monkeypatch.setitem(
        VENTURE_WORKFLOWS,
        "debate",
        {**VENTURE_WORKFLOWS["debate"], "run": fake_run},
    )
    app = create_app(settings=writable_settings, service=service)

    with TestClient(app) as client:
        catalog = client.get("/api/venture/workflows")
        assert catalog.status_code == 200
        assert [item["name"] for item in catalog.json()] == list(VENTURE_WORKFLOWS)
        assert all(
            set(item) == {"name", "label", "description"}
            for item in catalog.json()
        )
        assert client.post(
            "/api/venture/unknown", json={"topic": "Valid topic"}
        ).status_code == 404
        assert client.post(
            "/api/venture/debate", json={"topic": "   "}
        ).status_code == 400
        assert client.post(
            "/api/venture/debate", json={"topic": "x" * 501}
        ).status_code == 400

        started = client.post(
            "/api/venture/debate", json={"topic": "  A focused topic  "}
        )
        assert started.status_code == 202
        assert started.json() == {"started": True, "workflow": "debate"}
        assert called.wait(timeout=2)

    assert len(calls) == 1
    passed_service, passed_engine, topic, on_event = calls[0]
    assert passed_service is service
    assert passed_engine is app.state.engine
    assert topic == "A focused topic"
    assert on_event is None


def test_duplicate_workflow_returns_409(writable_settings, monkeypatch):
    service, _ = make_service(writable_settings, [])
    started = threading.Event()
    release = threading.Event()

    async def held_run(service, engine, topic, *, on_event=None):
        started.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return 321

    monkeypatch.setitem(
        VENTURE_WORKFLOWS,
        "debate",
        {**VENTURE_WORKFLOWS["debate"], "run": held_run},
    )
    app = create_app(settings=writable_settings, service=service)

    with TestClient(app) as client:
        first = client.post("/api/venture/debate", json={"topic": "One"})
        assert first.status_code == 202
        assert started.wait(timeout=2)
        duplicate = client.post("/api/venture/debate", json={"topic": "Two"})
        assert duplicate.status_code == 409
        release.set()
        for _ in range(100):
            if client.post(
                "/api/venture/debate", json={"topic": "Three"}
            ).status_code == 202:
                break
            time.sleep(0.01)
        else:
            pytest.fail("workflow lock was not released")
        release.set()
