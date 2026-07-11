"""Venture-layer persistence: memories, ideas, eval results, playbook files.

Mirrors app/api/reports.py: deterministic write paths used by validated tools
and workflows, plus read queries for the dashboard endpoints."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import EvalResult, Idea, Memory

# The 16 memory categories — the single source of truth for validation.
# Full semantics (save/retrieve/update/delete rules) live in docs/MEMORY_SYSTEM.md.
MEMORY_CATEGORIES = [
    "founder_profile",
    "business_idea",
    "active_business",
    "decision",
    "rejected_idea",
    "customer_research",
    "competitor_research",
    "financial_assumption",
    "product_roadmap",
    "marketing_experiment",
    "sales_conversation",
    "metric",
    "risk",
    "lesson_learned",
    "board_meeting",
    "agent_performance",
]

MAX_MEMORY_CONTENT = 4000
_EXCERPT_CHARS = 200


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- memories


def save_memory_record(
    engine: Engine,
    *,
    category: str,
    title: str,
    content: str,
    source_agent: str,
    related_idea: str | None = None,
) -> int:
    """The single deterministic write path for memories — used by the
    save_memory tool and by workflow code."""
    if category not in MEMORY_CATEGORIES:
        raise ValueError(f"invalid memory category {category!r}")
    now = _now()
    memory = Memory(
        category=category,
        title=title.strip()[:200],
        content=content.strip()[:MAX_MEMORY_CONTENT],
        source_agent=source_agent[:30],
        related_idea=(related_idea or "").strip()[:80] or None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    with Session(engine) as session:
        session.add(memory)
        session.commit()
        return memory.id


def list_memories(
    engine: Engine,
    *,
    category: str | None = None,
    status: str = "active",
    related_idea: str | None = None,
    limit: int = 100,
) -> list[dict]:
    stmt = select(Memory).order_by(Memory.created_at.desc(), Memory.id.desc()).limit(limit)
    if category:
        stmt = stmt.where(Memory.category == category)
    if status:
        stmt = stmt.where(Memory.status == status)
    if related_idea:
        stmt = stmt.where(Memory.related_idea == related_idea)
    with Session(engine) as session:
        rows = session.scalars(stmt).all()
    return [
        {
            "id": m.id,
            "category": m.category,
            "title": m.title,
            "content": m.content,
            "source_agent": m.source_agent,
            "related_idea": m.related_idea,
            "status": m.status,
            "created_at": m.created_at.isoformat() + "Z",
        }
        for m in rows
    ]


def archive_memory(engine: Engine, memory_id: int) -> bool:
    with Session(engine) as session:
        memory = session.get(Memory, memory_id)
        if memory is None:
            return False
        memory.status = "archived"
        memory.updated_at = _now()
        session.commit()
    return True


def memory_context(engine: Engine, *, related_idea: str | None = None, limit: int = 8) -> str:
    """Recent active memories rendered for a workflow brief ('' when none).
    Category-diverse: newest first, at most `limit` records."""
    records = list_memories(engine, related_idea=related_idea, limit=limit)
    if not records:
        return ""
    lines = [
        f"- [{m['category']}] {m['title']}: {m['content'][:300]}" for m in records
    ]
    return "RELEVANT MEMORY (prior decisions, research and lessons — do not re-litigate settled decisions without new evidence):\n" + "\n".join(lines)


# ------------------------------------------------------------------- ideas


def save_idea(
    engine: Engine,
    *,
    title: str,
    description: str,
    scores: dict[str, int],
    rationales: dict[str, str],
    total_score: float,
    verdict: str,
    best_version: str,
    worst_risk: str,
    validation_test: str,
    next_actions: list[str],
) -> int:
    """Written only by the score_idea tool after deterministic validation."""
    scores_payload = {
        key: {"score": scores[key], "rationale": (rationales.get(key) or "").strip()}
        for key in scores
    }
    idea = Idea(
        title=title.strip()[:200],
        description=description.strip(),
        scores_json=json.dumps(scores_payload),
        total_score=total_score,
        verdict=verdict,
        best_version=best_version.strip(),
        worst_risk=worst_risk.strip(),
        validation_test=validation_test.strip(),
        next_actions="\n".join(f"- {a.strip()}" for a in next_actions),
        created_at=_now(),
    )
    with Session(engine) as session:
        session.add(idea)
        session.commit()
        return idea.id


def _idea_dict(idea: Idea, *, full: bool) -> dict:
    data = {
        "id": idea.id,
        "title": idea.title,
        "total_score": idea.total_score,
        "verdict": idea.verdict,
        "created_at": idea.created_at.isoformat() + "Z",
    }
    if full:
        data.update(
            {
                "description": idea.description,
                "scores": json.loads(idea.scores_json),
                "best_version": idea.best_version,
                "worst_risk": idea.worst_risk,
                "validation_test": idea.validation_test,
                "next_actions": idea.next_actions,
            }
        )
    else:
        data["excerpt"] = idea.description[:_EXCERPT_CHARS]
    return data


def list_ideas(engine: Engine, *, limit: int = 50) -> list[dict]:
    stmt = select(Idea).order_by(Idea.created_at.desc(), Idea.id.desc()).limit(limit)
    with Session(engine) as session:
        rows = session.scalars(stmt).all()
    return [_idea_dict(i, full=False) for i in rows]


def get_idea(engine: Engine, idea_id: int) -> dict | None:
    with Session(engine) as session:
        idea = session.get(Idea, idea_id)
    if idea is None:
        return None
    return _idea_dict(idea, full=True)


# ------------------------------------------------------------ eval results


def save_eval_result(
    engine: Engine,
    *,
    case_id: str,
    agent: str,
    model: str,
    score: float,
    passed: bool,
    details: dict,
) -> int:
    result = EvalResult(
        case_id=case_id[:60],
        agent=agent[:30],
        model=model[:60],
        score=score,
        passed=passed,
        details_json=json.dumps(details),
        created_at=_now(),
    )
    with Session(engine) as session:
        session.add(result)
        session.commit()
        return result.id


def list_eval_results(engine: Engine, *, agent: str | None = None, limit: int = 200) -> list[dict]:
    stmt = (
        select(EvalResult)
        .order_by(EvalResult.created_at.desc(), EvalResult.id.desc())
        .limit(limit)
    )
    if agent:
        stmt = stmt.where(EvalResult.agent == agent)
    with Session(engine) as session:
        rows = session.scalars(stmt).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "agent": r.agent,
            "model": r.model,
            "score": r.score,
            "passed": r.passed,
            "details": json.loads(r.details_json),
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]


# --------------------------------------------------------------- playbooks

PLAYBOOKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "playbooks"
_SLUG_RE = re.compile(r"^[a-z0-9-]{1,60}$")


def list_playbooks() -> list[dict]:
    if not PLAYBOOKS_DIR.is_dir():
        return []
    playbooks = []
    for path in sorted(PLAYBOOKS_DIR.glob("*.md")):
        if path.stem == "README":
            continue
        title = path.stem.replace("-", " ").title()
        try:
            first = path.read_text(encoding="utf-8").splitlines()[0]
            if first.startswith("# "):
                title = first.removeprefix("# ").replace("Playbook:", "").strip()
        except (OSError, IndexError):
            pass
        playbooks.append({"slug": path.stem, "title": title})
    return playbooks


def get_playbook(slug: str) -> dict | None:
    if not _SLUG_RE.match(slug) or slug == "README":
        return None
    path = PLAYBOOKS_DIR / f"{slug}.md"
    if not path.is_file():
        return None
    return {"slug": slug, "content": path.read_text(encoding="utf-8")}
