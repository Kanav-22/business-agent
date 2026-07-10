"""Phase 4: Content sub-agent, human-in-the-loop approvals, competitor scans."""
from __future__ import annotations

import shutil

import pytest

from app.agents.service import AgentService
from app.api.approvals import list_approvals
from app.api.reports import list_reports
from app.db import make_engine
from app.main import create_app
from app.scheduler import run_weekly_competitor_scan
from app.tools.base import ToolError
from app.tools.content_writer import validate_content_input
from fastapi.testclient import TestClient
from tests.fake_anthropic import FakeClient, response, text_block, tool_use_block

DRAFT_BODY = (
    "Lumina Labs now supports usage-based billing on the Scale tier.\n\n"
    "Starting today, teams on Scale ($899/mo) can meter events instead of paying "
    "for seats they do not use. Existing customers keep their current pricing."
)


def make_service(settings, responses) -> tuple[AgentService, FakeClient]:
    fake = FakeClient(responses)
    return AgentService(settings, client_factory=lambda: fake), fake


def writable_settings(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    return settings


async def collect_events(service, message):
    events = []

    async def on_event(event):
        events.append(event)

    result, budget = await service.ask_ceo(message, on_event=on_event)
    return result, budget, events


def test_content_writer_validation():
    ok = {"title": "Launch post", "channel": "blog", "body": DRAFT_BODY}
    assert validate_content_input(ok)[1] == "blog"
    with pytest.raises(ToolError, match="title"):
        validate_content_input({**ok, "title": ""})
    with pytest.raises(ToolError, match="channel"):
        validate_content_input({**ok, "channel": "carrier-pigeon"})
    with pytest.raises(ToolError, match="at least"):
        validate_content_input({**ok, "body": "too short"})
    with pytest.raises(ToolError, match="at most"):
        validate_content_input({**ok, "body": "x" * 30_000})


async def test_cmo_commissions_content_draft_lands_in_approvals(settings, tmp_path):
    """The Phase 4 DoD chain: CEO → CMO → Content → content_writer → pending approval."""
    settings = writable_settings(settings, tmp_path)
    responses = {
        "CEO orchestrator": [
            response(
                [tool_use_block("tu_1", "delegate_to_agent",
                                {"agent": "cmo",
                                 "task": "Draft a launch announcement for usage-based billing."})],
                stop_reason="tool_use",
            ),
            response([text_block("The CMO commissioned a draft; it awaits approval.")]),
        ],
        "CMO agent": [
            response(
                [tool_use_block("tu_2", "delegate_to_agent",
                                {"agent": "content",
                                 "task": "Draft a blog launch announcement for usage-based "
                                         "billing on the Scale tier ($899/mo)."})],
                stop_reason="tool_use",
            ),
            response([text_block("Draft submitted to Approvals.")]),
        ],
        "Content agent": [
            response(
                [tool_use_block("tu_3", "content_writer",
                                {"title": "Usage-based billing on Scale",
                                 "channel": "blog",
                                 "body": DRAFT_BODY})],
                stop_reason="tool_use",
            ),
            response([text_block("Submitted draft #1 to the Approvals inbox.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    result, _, events = await collect_events(
        service, "Draft a launch announcement for usage-based billing"
    )
    assert result.error is None

    # delegation chain ceo(0) → cmo(1) → content(2)
    starts = {e["agent"]: e for e in events if e["type"] == "run_started"}
    assert starts["content"]["depth"] == 2
    assert starts["content"]["parent_run_id"] == starts["cmo"]["run_id"]

    submitted = next(
        e for e in events if e["type"] == "tool_result" and e["tool"] == "content_writer"
    )
    assert not submitted["is_error"]
    assert "Approvals inbox" in submitted["output"]

    engine = make_engine(settings.db_path)
    pending = list_approvals(engine, status="pending")
    assert len(pending) == 1
    draft = pending[0]
    assert draft["title"] == "Usage-based billing on Scale"
    assert draft["channel"] == "blog"
    assert draft["agent"] == "content"
    assert "usage-based billing" in draft["content"].lower()
    # nothing external happened: no published content report exists
    assert list_reports(engine, kind="content") == []


def test_approve_publishes_and_reject_does_not(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    service, _ = make_service(settings, [])
    engine = make_engine(settings.db_path)

    from app.api.approvals import create_approval

    a1 = create_approval(engine, kind="content", title="Post A", channel="blog",
                         agent="content", content=DRAFT_BODY)
    a2 = create_approval(engine, kind="content", title="Post B", channel="email",
                         agent="content", content=DRAFT_BODY)

    app = create_app(settings=settings, service=service)
    with TestClient(app) as client:
        # approve → status flips and a 'content' report is published
        res = client.post(f"/api/approvals/{a1}/approve")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "approved" and body["decided_at"]
        published = client.get(f"/api/reports/{body['published_report_id']}").json()
        assert published["kind"] == "content" and published["title"] == "Post A"

        # double-decide is refused
        assert client.post(f"/api/approvals/{a1}/reject").status_code == 409

        # reject → no publication
        res = client.post(f"/api/approvals/{a2}/reject", json={"note": "tone is off"})
        assert res.json()["status"] == "rejected"
        assert res.json()["note"] == "tone is off"

        assert client.post("/api/approvals/999/approve").status_code == 404

        pending = client.get("/api/approvals?status=pending").json()
        assert pending == []
        everything = client.get("/api/approvals").json()
        assert {a["status"] for a in everything} == {"approved", "rejected"}
        assert client.get("/api/approvals?status=bogus").status_code == 400

    reports = list_reports(engine, kind="content")
    assert [r["title"] for r in reports] == ["Post A"]


async def test_weekly_competitor_scan_saves_research_report(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    responses = {
        "Researcher agent": [
            response([text_block("Rival Analytics cut Pro to $79 (https://example.com/pricing). "
                                 "Implication: pressure on our starter tier.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    engine = make_engine(settings.db_path)
    report_id = await run_weekly_competitor_scan(service, engine)

    reports = list_reports(engine, kind="research")
    assert [r["id"] for r in reports] == [report_id]
    assert reports[0]["agent"] == "researcher"
    assert "Competitor scan" in reports[0]["title"]


def test_content_agent_wiring(settings):
    service, _ = make_service(settings, [])
    content = service.content_team["content"]
    # content has ONLY content_writer + server web search; no DB access
    assert content.config.tools == ["content_writer"]
    assert any(t["type"] == "web_search_20260209" for t in content.config.server_tools)
    # cmo can delegate to it
    cmo_tools = {t["name"] for t in service.specialists["cmo"].registry.schemas(
        service.specialists["cmo"].config.tools)}
    assert cmo_tools == {"sql_query", "delegate_to_agent"}
    # roster endpoint includes it
    assert "content" in {a.config.name for a in service.all_agents()}
