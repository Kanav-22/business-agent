"""Founder Clone: load/save the founder profile and render it as context for
venture agents. See docs/FOUNDER_CLONE_TEMPLATE.md for what each field means."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import FounderProfile

FOUNDER_KEYS = [
    "skills",
    "weaknesses",
    "working_style",
    "risk_tolerance",
    "budget_range",
    "long_term_goals",
    "current_assets",
    "coding_ability",
    "business_interests",
    "communication_style",
    "decision_flaws",
    "how_to_challenge",
    "how_to_focus",
    "distracting_ideas",
    "avoid",
    "double_down",
]

MAX_VALUE_CHARS = 1500


def get_founder_profile(engine: Engine) -> dict[str, str]:
    """All 16 keys, empty string where unset."""
    with Session(engine) as session:
        rows = session.scalars(select(FounderProfile)).all()
    stored = {r.key: r.value for r in rows}
    return {key: stored.get(key, "") for key in FOUNDER_KEYS}


def set_founder_profile(engine: Engine, values: dict) -> dict[str, str]:
    """Upsert the provided keys. Unknown keys are rejected; values are trimmed
    and capped. Returns the full profile after the write."""
    if not isinstance(values, dict):
        raise ValueError("profile must be an object of {key: value}.")
    unknown = sorted(set(values) - set(FOUNDER_KEYS))
    if unknown:
        raise ValueError(
            f"unknown founder profile keys: {', '.join(unknown)}. "
            f"Valid keys: {', '.join(FOUNDER_KEYS)}."
        )
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    with Session(engine) as session:
        for key, raw in values.items():
            value = str(raw or "").strip()[:MAX_VALUE_CHARS]
            row = session.get(FounderProfile, key)
            if row is None:
                session.add(FounderProfile(key=key, value=value, updated_at=now))
            else:
                row.value = value
                row.updated_at = now
        session.commit()
    return get_founder_profile(engine)


def founder_context(engine: Engine) -> str:
    """The profile rendered for prepending to venture task briefs. Empty string
    when the profile has never been filled in (agents then work generically and
    say so)."""
    profile = get_founder_profile(engine)
    filled = {k: v for k, v in profile.items() if v}
    if not filled:
        return ""
    lines = [f"- {key}: {value}" for key, value in filled.items()]
    return (
        "FOUNDER PROFILE (tailor every recommendation to this person; challenge "
        "them the way how_to_challenge says; respect avoid/budget constraints):\n"
        + "\n".join(lines)
    )
