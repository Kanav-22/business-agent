"""Venture layer: founder profile, memory store, survival mode, agent wiring,
and the new REST endpoints."""
from __future__ import annotations

import asyncio
import shutil

import pytest
from fastapi.testclient import TestClient

from app.agents.service import AgentService
from app.agents.simulated import _MARKERS
from app.agents.survival import apply_survival, survival_suffix
from app.api.venture import (
    MEMORY_CATEGORIES,
    archive_memory,
    list_memories,
    save_memory_record,
)
from app.db import make_engine
from app.main import create_app
from app.tools.base import ToolError
from app.tools.save_memory import make_save_memory_tool
from app.venture.founder import FOUNDER_KEYS, founder_context, set_founder_profile


@pytest.fixture()
def writable_settings(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    return settings


@pytest.fixture()
def writable_engine(writable_settings):
    return make_engine(writable_settings.db_path)


def make_service(settings) -> AgentService:
    return AgentService(settings, client_factory=lambda: None)


# -------------------------------------------------------------- founder clone


def test_founder_profile_roundtrip_and_context(writable_engine):
    assert founder_context(writable_engine) == ""  # unset profile → no context
    profile = set_founder_profile(
        writable_engine, {"skills": "Python, writing", "budget_range": "₹50,000"}
    )
    assert profile["skills"] == "Python, writing"
    assert set(profile) == set(FOUNDER_KEYS)
    context = founder_context(writable_engine)
    assert "FOUNDER PROFILE" in context and "₹50,000" in context

    with pytest.raises(ValueError, match="unknown founder profile keys"):
        set_founder_profile(writable_engine, {"favourite_colour": "blue"})


# ------------------------------------------------------------------- memories


class Ctx:
    agent = "risk"
    run_id = "test"
    depth = 0
    budget = None
    on_event = None
    extra = None


def test_save_memory_tool_enforces_least_privilege(writable_engine):
    tool = make_save_memory_tool(writable_engine, ["risk"])
    ok = {"category": "risk", "title": "Platform risk", "content": "WhatsApp policy."}
    result = asyncio.run(tool.handler(ok, Ctx()))
    assert "Saved memory" in result

    with pytest.raises(ToolError, match="may only save"):
        asyncio.run(tool.handler({**ok, "category": "decision"}, Ctx()))
    with pytest.raises(ToolError, match="invalid category"):
        asyncio.run(tool.handler({**ok, "category": "gossip"}, Ctx()))
    with pytest.raises(ToolError, match="title"):
        asyncio.run(tool.handler({**ok, "title": ""}, Ctx()))
    with pytest.raises(ToolError, match="exceeds"):
        asyncio.run(tool.handler({**ok, "content": "x" * 5000}, Ctx()))

    with pytest.raises(ValueError, match="unknown memory categories"):
        make_save_memory_tool(writable_engine, ["not_a_category"])


def test_memory_lifecycle(writable_engine):
    memory_id = save_memory_record(
        writable_engine,
        category="decision",
        title="Pilot, not launch",
        content="Debate decided a 3-clinic pilot.",
        source_agent="ceo",
        related_idea="ai-booking-doctors",
    )
    active = list_memories(writable_engine, category="decision")
    assert [m["id"] for m in active] == [memory_id]
    assert active[0]["related_idea"] == "ai-booking-doctors"

    assert archive_memory(writable_engine, memory_id)
    assert list_memories(writable_engine, category="decision") == []
    archived = list_memories(writable_engine, category="decision", status="archived")
    assert len(archived) == 1
    assert not archive_memory(writable_engine, 99_999)

    with pytest.raises(ValueError, match="invalid memory category"):
        save_memory_record(
            writable_engine, category="bad", title="t", content="c", source_agent="x"
        )


# ------------------------------------------------- survival mode + wiring


def test_survival_suffix_extracted_from_guides():
    assert "ROUTER and SYNTHESIZER" in survival_suffix("ceo")
    assert survival_suffix("nonexistent_agent") == ""
    prompt = "You are the CEO orchestrator agent of Lumina Labs."
    assert apply_survival("ceo", prompt, enabled=False) == prompt
    boosted = apply_survival("ceo", prompt, enabled=True)
    assert boosted.startswith(prompt) and "Survival scaffolding" in boosted


def test_service_wiring_default_and_flags(settings):
    service = make_service(settings)
    # Venture team exists and is NOT in the CEO chat roster by default.
    assert set(service.venture_team) == {
        "venture_ceo", "venture_cfo", "venture_cmo", "venture_cto",
        "coo", "risk", "red_team", "sales", "interviewer", "scorer",
    }
    delegate = service.ceo.registry.schemas(["delegate_to_agent"])[0]
    default_enum = delegate["input_schema"]["properties"]["agent"]["enum"]
    assert default_enum == sorted(service.specialists)
    assert "Survival scaffolding" not in service.ceo.config.system_prompt

    settings.venture_in_chat = True
    merged = make_service(settings)
    merged_enum = merged.ceo.registry.schemas(["delegate_to_agent"])[0][
        "input_schema"]["properties"]["agent"]["enum"]
    assert "red_team" in merged_enum and set(default_enum) < set(merged_enum)
    settings.venture_in_chat = False

    settings.survival_mode = True
    boosted = make_service(settings)
    assert "Survival scaffolding" in boosted.ceo.config.system_prompt
    assert "This is risk triage" in boosted.venture_team["risk"].config.system_prompt
    settings.survival_mode = False


def test_every_agent_prompt_resolves_to_its_own_demo_handler(settings):
    """The demo-mode marker table must uniquely identify every agent —
    including the new venture agents — from its system prompt."""
    service = make_service(settings)
    for agent in service.all_agents():
        matched = next(
            (name for marker, name in _MARKERS if marker in agent.config.system_prompt),
            None,
        )
        assert matched == agent.config.name, (
            f"{agent.config.name} resolved to {matched!r} in demo mode"
        )


# ---------------------------------------------------------------- REST API


def test_venture_endpoints(writable_settings):
    service = make_service(writable_settings)
    client = TestClient(create_app(writable_settings, service))

    # Router: the doctor example from the spec.
    routed = client.post(
        "/api/route", json={"message": "I want to launch an AI tool for doctors."}
    )
    assert routed.status_code == 200
    body = routed.json()
    assert body["primary_agent"] == "ceo" and body["risk_level"] == "high"
    assert "risk" in body["supporting_agents"]
    assert client.post("/api/route", json={"message": "  "}).status_code == 400

    # Founder profile.
    put = client.put("/api/founder", json={"values": {"skills": "Python"}})
    assert put.status_code == 200 and put.json()["skills"] == "Python"
    assert client.get("/api/founder").json()["skills"] == "Python"
    bad = client.put("/api/founder", json={"values": {"nope": "x"}})
    assert bad.status_code == 400

    # Memories.
    engine = make_engine(writable_settings.db_path)
    memory_id = save_memory_record(
        engine, category="risk", title="t", content="c", source_agent="risk"
    )
    memories = client.get("/api/memories", params={"category": "risk"}).json()
    assert [m["id"] for m in memories] == [memory_id]
    assert client.post(f"/api/memories/{memory_id}/archive").status_code == 200
    assert client.post("/api/memories/99999/archive").status_code == 404

    # Ideas (empty DB → empty list, 404 detail).
    assert client.get("/api/ideas").json() == []
    assert client.get("/api/ideas/1").status_code == 404

    # Playbooks served from docs/.
    playbooks = client.get("/api/playbooks").json()
    slugs = {p["slug"] for p in playbooks}
    assert "ai-automation-agency" in slugs and len(playbooks) == 12
    detail = client.get("/api/playbooks/micro-saas")
    assert detail.status_code == 200
    assert "# Playbook: Micro-SaaS" in detail.json()["content"]
    assert client.get("/api/playbooks/README").status_code == 404
    assert client.get("/api/playbooks/../secrets").status_code in (400, 404)

    # Evals endpoint exists (results land in Phase V4).
    assert client.get("/api/evals").json() == []

    # Memory categories doc constant matches the 16 in the design doc.
    assert len(MEMORY_CATEGORIES) == 16
