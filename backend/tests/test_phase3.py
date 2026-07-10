"""Phase 3: finance sub-team, report_writer, reports API, scheduled jobs."""
from __future__ import annotations

import shutil

import pytest

from app.agents.budget import TokenBudget
from app.agents.service import AgentService
from app.api.reports import get_report, list_reports, save_report
from app.db import make_engine
from app.main import create_app
from app.scheduler import create_scheduler, run_weekly_briefing, run_weekly_control
from app.tools.base import ToolError
from app.tools.report_writer import validate_report_input
from fastapi.testclient import TestClient
from tests.fake_anthropic import FakeClient, response, text_block, tool_use_block


def make_service(settings, responses) -> tuple[AgentService, FakeClient]:
    fake = FakeClient(responses)
    return AgentService(settings, client_factory=lambda: fake), fake


def writable_settings(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    return settings


async def _noop(event):
    return None


def test_finance_team_shape(settings):
    service, _ = make_service(settings, [])
    assert set(service.finance_team) == {"fpa", "reporting", "revenue", "control"}
    # CFO is now an orchestrator: delegation only, no direct data access
    assert service.specialists["cfo"].config.tools == ["delegate_to_agent"]
    # least privilege on the sub-team
    revenue_doc = service.finance_team["revenue"].registry.schemas(["sql_query"])[0]["description"]
    assert "invoices(" in revenue_doc and "transactions(" not in revenue_doc
    control_doc = service.finance_team["control"].registry.schemas(["sql_query"])[0]["description"]
    assert "campaigns(" in control_doc and "projects(" not in control_doc


def test_report_writer_validation():
    with pytest.raises(ToolError, match="title"):
        validate_report_input({"title": "", "sections": [{"heading": "a", "content": "b"}]})
    with pytest.raises(ToolError, match="sections"):
        validate_report_input({"title": "T", "sections": []})
    with pytest.raises(ToolError, match="heading and content"):
        validate_report_input({"title": "T", "sections": [{"heading": "a", "content": ""}]})
    with pytest.raises(ToolError, match="exceeds"):
        validate_report_input(
            {"title": "T", "sections": [{"heading": "a", "content": "x" * 9000}]}
        )
    title, sections = validate_report_input(
        {"title": " P&L ", "sections": [{"heading": "Summary", "content": "All good."}]}
    )
    assert title == "P&L" and sections[0]["heading"] == "Summary"


async def test_reporting_agent_saves_report(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    responses = {
        "Reporting agent": [
            response(
                [tool_use_block("tu_1", "sql_query",
                                {"query": "SELECT strftime('%Y-%m', date) AS m, SUM(amount) "
                                          "FROM transactions WHERE type='revenue' GROUP BY m "
                                          "ORDER BY m DESC LIMIT 1"})],
                stop_reason="tool_use",
            ),
            response(
                [tool_use_block("tu_2", "report_writer",
                                {"title": "Monthly P&L — June 2026",
                                 "sections": [
                                     {"heading": "Revenue", "content": "Subscription revenue: $47,959."},
                                     {"heading": "Verdict", "content": "Burn within plan."},
                                 ]})],
                stop_reason="tool_use",
            ),
            response([text_block("Saved the P&L report.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    result = await service.finance_team["reporting"].run(
        "Produce the monthly P&L report.",
        on_event=_noop,
        budget=TokenBudget(limit=50_000),
    )
    assert result.error is None

    engine = make_engine(settings.db_path)
    reports = list_reports(engine)
    assert len(reports) == 1
    assert reports[0]["title"] == "Monthly P&L — June 2026"
    assert reports[0]["kind"] == "report" and reports[0]["agent"] == "reporting"
    full = get_report(engine, reports[0]["id"])
    assert "## Revenue" in full["content"]
    assert "$47,959" in full["content"]


async def test_weekly_control_job_saves_control_check(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    responses = {
        "Control agent": [
            response(
                [tool_use_block("tu_1", "sql_query",
                                {"query": "SELECT COUNT(*) FROM invoices WHERE status='overdue'"})],
                stop_reason="tool_use",
            ),
            response([text_block("[OK] Billing reconciles.\n[WARN] 12 overdue invoices.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    engine = make_engine(settings.db_path)
    report_id = await run_weekly_control(service, engine)

    report = get_report(engine, report_id)
    assert report["kind"] == "control_check"
    assert report["agent"] == "control"
    assert "[WARN]" in report["content"]


async def test_weekly_briefing_job_saves_briefing(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    responses = {
        "CEO orchestrator": [
            response(
                [tool_use_block("tu_1", "delegate_to_agent",
                                {"agent": "cto", "task": "Projects at risk?"})],
                stop_reason="tool_use",
            ),
            response([text_block("Per the CTO, two projects are at risk this week.")]),
        ],
        "CTO agent": [
            response([text_block("Two projects at risk.")]),
        ],
    }
    service, _ = make_service(settings, responses)
    engine = make_engine(settings.db_path)
    report_id = await run_weekly_briefing(service, engine)

    report = get_report(engine, report_id)
    assert report["kind"] == "briefing" and report["agent"] == "ceo"
    assert "Per the CTO" in report["content"]


def test_scheduler_has_all_weekly_jobs(settings):
    service, _ = make_service(settings, [])
    scheduler = create_scheduler(service, service.engine)
    jobs = {j.id for j in scheduler.get_jobs()}
    assert jobs == {"weekly_control", "weekly_briefing", "weekly_competitor_scan"}


def test_reports_api_and_download(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    service, _ = make_service(settings, [])
    engine = make_engine(settings.db_path)
    rid = save_report(
        engine,
        title="Test report",
        content="# Test report\n\n## Numbers\nAll fine.\n",
        agent="reporting",
        kind="report",
    )
    app = create_app(settings=settings, service=service)
    with TestClient(app) as client:
        listed = client.get("/api/reports").json()
        assert [r["id"] for r in listed] == [rid]
        assert listed[0]["excerpt"].startswith("All fine")

        detail = client.get(f"/api/reports/{rid}").json()
        assert detail["content"].startswith("# Test report")

        download = client.get(f"/api/reports/{rid}/download")
        assert download.status_code == 200
        assert "attachment" in download.headers["content-disposition"]

        assert client.get("/api/reports/99999").status_code == 404
        # no briefing yet
        assert client.get("/api/briefing").json() == {"report": None}


def test_job_trigger_endpoint(settings, tmp_path):
    settings = writable_settings(settings, tmp_path)
    responses = {
        "Control agent": [response([text_block("[OK] All five checks pass.")])],
    }
    service, _ = make_service(settings, responses)
    app = create_app(settings=settings, service=service)
    with TestClient(app) as client:
        assert client.post("/api/jobs/nope/run").status_code == 404
        res = client.post("/api/jobs/weekly_control/run")
        assert res.status_code == 202
        assert res.json() == {"started": True, "job": "weekly_control"}

    # TestClient shutdown drains pending tasks — the report should exist now.
    engine = make_engine(settings.db_path)
    reports = list_reports(engine, kind="control_check")
    assert len(reports) == 1
    assert "Weekly control check" in reports[0]["title"]
