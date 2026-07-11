"""Business intake questions, durable profile storage, and agent context."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import BusinessProfile

INTAKE_QUESTIONS: list[dict] = [
    {
        "key": "name",
        "section": "Identity",
        "question": "What is the business called?",
        "type": "short",
        "required": True,
        "why": "Gives the team a clear name for reports, decisions, and memories.",
    },
    {
        "key": "description_own_words",
        "section": "Identity",
        "question": (
            "Explain your business in your own words — what you sell, to whom, "
            "and how it makes money. Write like you're telling a friend."
        ),
        "type": "long",
        "required": True,
        "why": "Your language preserves context that a category or form field would miss.",
    },
    {
        "key": "founded",
        "section": "Identity",
        "question": "When did it start, and what stage is it at?",
        "type": "short",
        "required": False,
        "why": "Stage and age change which recommendations are realistic.",
    },
    {
        "key": "situation_own_words",
        "section": "Situation",
        "question": (
            "Describe the current situation in your own words — what's going well, "
            "what's stuck, and what happened recently that matters."
        ),
        "type": "long",
        "required": True,
        "why": "The team needs your unfiltered view before it forms its own diagnosis.",
    },
    {
        "key": "decision_pending",
        "section": "Situation",
        "question": "What decisions are you facing right now?",
        "type": "long",
        "required": False,
        "why": "Surfaces decisions where analysis can be useful immediately.",
    },
    {
        "key": "biggest_worries",
        "section": "Situation",
        "question": "What are your biggest worries about the business right now?",
        "type": "long",
        "required": True,
        "why": "Helps the team test downside risk instead of assuming only the happy path.",
    },
    {
        "key": "customers_who",
        "section": "Customers",
        "question": "Who buys from you? Describe your 2-3 main customer types.",
        "type": "long",
        "required": True,
        "why": "Grounds positioning, sales, and product advice in real buyers.",
    },
    {
        "key": "why_customers_buy",
        "section": "Customers",
        "question": "Why do customers buy from you, in their words if you know them?",
        "type": "long",
        "required": False,
        "why": "Reveals the job customers actually hire the business to do.",
    },
    {
        "key": "customer_count",
        "section": "Customers",
        "question": "Roughly how many paying customers?",
        "type": "short",
        "required": False,
        "why": "Provides scale without asking for false precision.",
    },
    {
        "key": "revenue_monthly",
        "section": "Money",
        "question": "Monthly revenue, roughly — a range is fine.",
        "type": "short",
        "required": True,
        "why": "Anchors financial recommendations to the business's actual scale.",
    },
    {
        "key": "pricing_summary",
        "section": "Money",
        "question": "What do you charge, and how is it structured?",
        "type": "long",
        "required": True,
        "why": "Pricing structure drives revenue quality, sales friction, and margin.",
    },
    {
        "key": "costs_summary",
        "section": "Money",
        "question": "What are your main costs, roughly?",
        "type": "long",
        "required": False,
        "why": "Lets the finance team distinguish revenue from sustainable economics.",
    },
    {
        "key": "margins_estimate",
        "section": "Money",
        "question": "What is your best estimate of gross or contribution margin?",
        "type": "short",
        "required": False,
        "why": "An estimate exposes an assumption the team can validate later.",
    },
    {
        "key": "team",
        "section": "Operations",
        "question": "Who works in the business and on what?",
        "type": "long",
        "required": False,
        "why": "Plans need owners and must fit the capacity that really exists.",
    },
    {
        "key": "tools_systems",
        "section": "Operations",
        "question": "What software or tools run the business?",
        "type": "long",
        "required": False,
        "why": "Shows where data lives and what can be improved without a rebuild.",
    },
    {
        "key": "process_pain",
        "section": "Operations",
        "question": "Which repeated tasks eat the most time?",
        "type": "long",
        "required": False,
        "why": "Highlights operating bottlenecks and useful automation opportunities.",
    },
    {
        "key": "sales_channels",
        "section": "Growth",
        "question": "How do customers find you and how do you close them?",
        "type": "long",
        "required": True,
        "why": "Connects demand generation to the actual sales process.",
    },
    {
        "key": "marketing_summary",
        "section": "Growth",
        "question": "What marketing are you doing now, and what seems to work?",
        "type": "long",
        "required": False,
        "why": "Prevents the team from discarding useful evidence or repeating failed work.",
    },
    {
        "key": "cac_knowledge",
        "section": "Growth",
        "question": "Do you know your customer acquisition cost? If yes, what is it?",
        "type": "short",
        "required": False,
        "why": "Makes acquisition economics explicit, including when they are unknown.",
    },
    {
        "key": "competitors",
        "section": "Market",
        "question": "Who do customers compare you with, including doing nothing?",
        "type": "long",
        "required": False,
        "why": "Defines the real alternatives rather than an abstract market category.",
    },
    {
        "key": "differentiation",
        "section": "Market",
        "question": "Why do customers pick you over the alternatives?",
        "type": "long",
        "required": False,
        "why": "Captures the advantage the business believes it can defend.",
    },
    {
        "key": "goals_12mo",
        "section": "Direction",
        "question": "What must be true 12 months from now for you to call the year successful?",
        "type": "long",
        "required": True,
        "why": "Gives every recommendation a shared destination and time horizon.",
    },
    {
        "key": "constraints",
        "section": "Direction",
        "question": "What are the hard constraints: budget, time, people, or regulations?",
        "type": "long",
        "required": False,
        "why": "Keeps plans inside the boundaries the owner cannot wish away.",
    },
    {
        "key": "avoid",
        "section": "Direction",
        "question": "Anything you've decided NOT to do?",
        "type": "long",
        "required": False,
        "why": "Preserves deliberate boundaries so agents do not reopen settled choices.",
    },
]

BUSINESS_KEYS = [question["key"] for question in INTAKE_QUESTIONS]
INTAKE_SECTIONS = list(dict.fromkeys(question["section"] for question in INTAKE_QUESTIONS))
_QUESTION_BY_KEY = {question["key"]: question for question in INTAKE_QUESTIONS}
_VALUE_CAPS = {"long": 4000, "short": 1500, "number": 1500, "choice": 1500}

UPLOAD_MANIFEST: list[dict] = [
    {
        "key": "transactions_csv",
        "label": "Transactions CSV",
        "accepts": ".csv",
        "purpose": (
            "Loaded into the live database via the V6 importer — use the templates "
            "in docs/templates/."
        ),
    },
    {
        "key": "customers_csv",
        "label": "Customers CSV",
        "accepts": ".csv",
        "purpose": (
            "Loaded into the live database via the V6 importer — use the templates "
            "in docs/templates/."
        ),
    },
    {
        "key": "invoices_csv",
        "label": "Invoices CSV",
        "accepts": ".csv",
        "purpose": (
            "Loaded into the live database via the V6 importer — use the templates "
            "in docs/templates/."
        ),
    },
    {
        "key": "context_docs",
        "label": "Context documents",
        "accepts": ".txt,.md",
        "purpose": (
            "Narrative material — plans, notes, and pitch text — stored as intake "
            "documents for the analyst review."
        ),
    },
]

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def get_business_profile(engine: Engine) -> dict[str, str]:
    """Return every intake key, using an empty string for an unset answer."""
    with Session(engine) as session:
        rows = session.scalars(select(BusinessProfile)).all()
    stored = {row.key: row.value for row in rows}
    return {key: stored.get(key, "") for key in BUSINESS_KEYS}


def set_business_profile(engine: Engine, values: dict) -> dict[str, str]:
    """Upsert an intake subset after key validation, trimming, and type caps."""
    if not isinstance(values, dict):
        raise ValueError("profile must be an object of {key: value}.")
    unknown = sorted(set(values) - set(BUSINESS_KEYS))
    if unknown:
        raise ValueError(
            f"unknown business profile keys: {', '.join(unknown)}. "
            f"Valid keys: {', '.join(BUSINESS_KEYS)}."
        )

    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    with Session(engine) as session:
        for key, raw in values.items():
            question_type = _QUESTION_BY_KEY[key]["type"]
            value = str(raw or "").strip()[: _VALUE_CAPS[question_type]]
            row = session.get(BusinessProfile, key)
            if row is None:
                session.add(BusinessProfile(key=key, value=value, updated_at=now))
            else:
                row.value = value
                row.updated_at = now
        session.commit()
    return get_business_profile(engine)


def business_context(engine: Engine) -> str:
    """Render filled owner answers for agents, or ``""`` when none exist."""
    filled = {key: value for key, value in get_business_profile(engine).items() if value}
    if not filled:
        return ""
    lines = [f"- {key}: {value}" for key, value in filled.items()]
    return (
        "BUSINESS PROFILE (owner-provided context; treat estimates as assumptions "
        "until validated):\n" + "\n".join(lines)
    )


def upload_manifest_entry(kind: str) -> dict | None:
    return next((entry for entry in UPLOAD_MANIFEST if entry["key"] == kind), None)


def sanitized_filename(filename: str | None) -> str:
    """Return a bounded basename safe for report titles and local staging."""
    basename = Path((filename or "").replace("\\", "/")).name
    cleaned = _SAFE_FILENAME_RE.sub("_", basename).strip(" .")
    if not cleaned:
        raise ValueError("file must have a valid filename")
    suffix = Path(cleaned).suffix[:16]
    stem = Path(cleaned).stem[: max(1, 120 - len(suffix))].strip(" .") or "upload"
    return f"{stem}{suffix}"[:120]
