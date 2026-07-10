"""Scheduled operations (Phase 3): every Monday morning the system produces a
control check and a CEO briefing on its own — no one has to ask.

Job runs stream their events to the JSONL decision log only (no websocket),
so they show up on the Agent Activity page like any other run. The final
outputs are persisted to the reports library by deterministic code.
"""
from __future__ import annotations

import datetime as dt
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.engine import Engine

from app.agents.budget import TokenBudget
from app.api.reports import save_report

log = logging.getLogger("business-agent.scheduler")

CONTROL_TASK = """\
Run the full weekly reconciliation and anomaly check (all five standard checks: \
billing reconciliation, payroll reconciliation, marketing reconciliation, invoices, \
month-over-month anomalies). Report every check as [OK] / [WARN] / [CRITICAL] with \
the numbers that prove it, then finish with a one-line overall verdict."""

BRIEFING_TASK = """\
Produce the weekly CEO briefing. Delegate in parallel and cover: (1) financial \
position — last month's profit, current cash and runway (cfo); (2) marketing — \
new-customer trend and the best/worst channel by CAC (cmo); (3) engineering — \
projects at risk and their deadlines (cto); (4) blocked work across departments \
(coordinator). Synthesize into a brief of at most ~300 words with clear attribution \
per specialist. This is a scheduled report — do not address the reader directly."""

COMPETITOR_SCAN_TASK = """\
Run the weekly competitor scan for Lumina Labs (B2B SaaS analytics; plans at \
$99/$299/$899 per month). Search the web for, from roughly the past week: (1) pricing \
changes or notable pricing pages among analytics/BI competitors; (2) significant \
product launches or feature announcements in the analytics space; (3) funding, M&A or \
shutdown news among comparable companies. Cite the URL for every claim. Finish with \
2-3 concrete implications for Lumina Labs. This is a scheduled report — do not \
address the reader directly."""


async def _noop_event(event: dict) -> None:
    return None


async def run_weekly_control(service, engine: Engine) -> int:
    """Control agent reconciliation + anomaly check → reports library."""
    today = dt.date.today().isoformat()
    result = await service.finance_team["control"].run(
        CONTROL_TASK,
        on_event=_noop_event,
        budget=TokenBudget(limit=service.settings.token_budget),
    )
    content = result.output or "(no output)"
    if result.error:
        content = f"> ⚠ Run ended with error: {result.error}\n\n{content}"
    report_id = save_report(
        engine,
        title=f"Weekly control check — {today}",
        content=f"# Weekly control check — {today}\n\n{content}\n",
        agent="control",
        kind="control_check",
    )
    log.info("weekly control check saved as report #%s", report_id)
    return report_id


async def run_weekly_briefing(service, engine: Engine) -> int:
    """CEO briefing (fans out to the C-suite) → reports library + Overview."""
    today = dt.date.today().isoformat()
    result, _budget = await service.ask_ceo(BRIEFING_TASK, on_event=_noop_event)
    content = result.output or "(no output)"
    if result.error:
        content = f"> ⚠ Run ended with error: {result.error}\n\n{content}"
    report_id = save_report(
        engine,
        title=f"CEO weekly briefing — {today}",
        content=f"# CEO weekly briefing — {today}\n\n{content}\n",
        agent="ceo",
        kind="briefing",
    )
    log.info("weekly briefing saved as report #%s", report_id)
    return report_id


async def run_weekly_competitor_scan(service, engine: Engine) -> int:
    """Researcher competitor scan (server-side web search) → reports library."""
    today = dt.date.today().isoformat()
    result = await service.specialists["researcher"].run(
        COMPETITOR_SCAN_TASK,
        on_event=_noop_event,
        budget=TokenBudget(limit=service.settings.token_budget),
    )
    content = result.output or "(no output)"
    if result.error:
        content = f"> ⚠ Run ended with error: {result.error}\n\n{content}"
    report_id = save_report(
        engine,
        title=f"Competitor scan — {today}",
        content=f"# Competitor scan — {today}\n\n{content}\n",
        agent="researcher",
        kind="research",
    )
    log.info("weekly competitor scan saved as report #%s", report_id)
    return report_id


JOBS = {
    "weekly_control": run_weekly_control,
    "weekly_briefing": run_weekly_briefing,
    "weekly_competitor_scan": run_weekly_competitor_scan,
}


def create_scheduler(service, engine: Engine) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_weekly_control,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        args=[service, engine],
        id="weekly_control",
        name="Weekly control check (reconciliation + anomalies)",
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.add_job(
        run_weekly_briefing,
        CronTrigger(day_of_week="mon", hour=6, minute=20),
        args=[service, engine],
        id="weekly_briefing",
        name="Weekly CEO briefing",
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.add_job(
        run_weekly_competitor_scan,
        CronTrigger(day_of_week="mon", hour=6, minute=40),
        args=[service, engine],
        id="weekly_competitor_scan",
        name="Weekly competitor scan (Researcher)",
        misfire_grace_time=3600,
        coalesce=True,
    )
    return scheduler
