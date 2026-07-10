"""Report persistence + queries. save_report is the single deterministic write
path used by both the report_writer tool and the scheduled jobs."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Report

_EXCERPT_CHARS = 220


def save_report(engine: Engine, *, title: str, content: str, agent: str, kind: str) -> int:
    report = Report(
        title=title[:200],
        kind=kind,
        agent=agent,
        created_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
        content=content,
    )
    with Session(engine) as session:
        session.add(report)
        session.commit()
        return report.id


def _excerpt(content: str) -> str:
    text = " ".join(
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    return text[:_EXCERPT_CHARS] + ("…" if len(text) > _EXCERPT_CHARS else "")


def list_reports(engine: Engine, *, kind: str | None = None, limit: int = 50) -> list[dict]:
    stmt = select(Report).order_by(Report.created_at.desc(), Report.id.desc()).limit(limit)
    if kind:
        stmt = stmt.where(Report.kind == kind)
    with Session(engine) as session:
        reports = session.scalars(stmt).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "kind": r.kind,
            "agent": r.agent,
            "created_at": r.created_at.isoformat() + "Z",
            "excerpt": _excerpt(r.content),
        }
        for r in reports
    ]


def get_report(engine: Engine, report_id: int) -> dict | None:
    with Session(engine) as session:
        r = session.get(Report, report_id)
    if r is None:
        return None
    return {
        "id": r.id,
        "title": r.title,
        "kind": r.kind,
        "agent": r.agent,
        "created_at": r.created_at.isoformat() + "Z",
        "content": r.content,
    }
