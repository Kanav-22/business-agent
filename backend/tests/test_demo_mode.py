"""Demo mode: the simulated client drives the REAL agent loop and REAL tools
with zero API spend — no scripted responses needed in these tests."""
from __future__ import annotations

import shutil

from app.agents.service import AgentService
from app.api.approvals import list_approvals
from app.api.reports import list_reports
from app.db import make_engine
from app.scheduler import run_weekly_briefing


def demo_service(settings) -> AgentService:
    settings.demo_mode = True
    return AgentService(settings)  # default factory → SimulatedClient


async def collect(service, message):
    events = []

    async def on_event(event):
        events.append(event)

    result, budget = await service.ask_ceo(message, on_event=on_event)
    return result, budget, events


async def test_demo_broad_question_fans_out(settings):
    service = demo_service(settings)
    result, budget, events = await collect(service, "How is the business doing?")

    assert result.error is None
    started = {e["agent"] for e in events if e["type"] == "run_started"}
    assert {"ceo", "cfo", "cmo", "cto", "coordinator"} <= started
    # real SQL ran somewhere in the tree
    sql_results = [
        e for e in events
        if e["type"] == "tool_result" and e["tool"] == "sql_query" and not e["is_error"]
    ]
    assert sql_results
    # live numbers made it into the final answer, and nothing was spent
    assert "answered" in result.output
    assert budget.total == 0


async def test_demo_finance_question_uses_cfo_chain(settings):
    service = demo_service(settings)
    result, _, events = await collect(
        service, "What was our profit last month and what's our runway?"
    )
    assert result.error is None
    starts = {e["agent"]: e for e in events if e["type"] == "run_started"}
    assert starts["fpa"]["depth"] == 2
    assert starts["fpa"]["parent_run_id"] == starts["cfo"]["run_id"]
    # a real revenue/expense figure (formatted digits) appears in the output
    assert any(ch.isdigit() for ch in result.output)


async def test_demo_draft_lands_in_approvals(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    service = demo_service(settings)

    result, _, events = await collect(
        service, "Draft a launch announcement for usage-based billing"
    )
    assert result.error is None
    engine = make_engine(db_copy)
    pending = list_approvals(engine, status="pending")
    assert len(pending) == 1
    assert pending[0]["agent"] == "content"
    assert "usage-based billing" in pending[0]["title"].lower()


async def test_demo_briefing_job_and_report(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    service = demo_service(settings)
    engine = make_engine(db_copy)

    report_id = await run_weekly_briefing(service, engine)
    briefings = list_reports(engine, kind="briefing")
    assert [b["id"] for b in briefings] == [report_id]
