"""Approvals inbox persistence + decisions.

create_approval is the deterministic write path used by the content_writer
tool; decide_approval flips a pending item exactly once.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Approval


class AlreadyDecided(Exception):
    pass


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _to_dict(a: Approval) -> dict:
    return {
        "id": a.id,
        "kind": a.kind,
        "title": a.title,
        "channel": a.channel,
        "agent": a.agent,
        "status": a.status,
        "content": a.content,
        "created_at": a.created_at.isoformat() + "Z",
        "decided_at": a.decided_at.isoformat() + "Z" if a.decided_at else None,
        "note": a.note,
    }


def create_approval(
    engine: Engine, *, kind: str, title: str, channel: str, agent: str, content: str
) -> int:
    approval = Approval(
        kind=kind,
        title=title[:200],
        channel=channel,
        agent=agent,
        status="pending",
        content=content,
        created_at=_now(),
    )
    with Session(engine) as session:
        session.add(approval)
        session.commit()
        return approval.id


def list_approvals(engine: Engine, *, status: str | None = None, limit: int = 100) -> list[dict]:
    stmt = select(Approval).order_by(Approval.created_at.desc(), Approval.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(Approval.status == status)
    with Session(engine) as session:
        return [_to_dict(a) for a in session.scalars(stmt).all()]


def get_approval(engine: Engine, approval_id: int) -> dict | None:
    with Session(engine) as session:
        a = session.get(Approval, approval_id)
    return _to_dict(a) if a else None


def decide_approval(
    engine: Engine, approval_id: int, *, approve: bool, note: str | None = None
) -> dict | None:
    """Returns the updated approval, None if missing; raises AlreadyDecided."""
    with Session(engine) as session:
        a = session.get(Approval, approval_id)
        if a is None:
            return None
        if a.status != "pending":
            raise AlreadyDecided(f"approval #{approval_id} is already {a.status}")
        a.status = "approved" if approve else "rejected"
        a.decided_at = _now()
        a.note = (note or "").strip()[:300] or None
        session.commit()
        return _to_dict(a)
