"""V7 business intake: interview data, context, uploads, and analyst review."""
from __future__ import annotations

import hashlib
import inspect
import shutil

import pytest
from fastapi.testclient import TestClient

from app.agents import service as service_module
from app.agents.service import AgentService
from app.agents.simulated import _MARKERS
from app.api.reports import get_report, list_reports, save_report
from app.api.venture import list_memories
from app.db import make_engine
from app.main import create_app
from app.venture import intake as intake_module
from app.venture.intake import (
    BUSINESS_KEYS,
    DEFAULT_COMPANY_CONTEXT,
    INTAKE_QUESTIONS,
    UPLOAD_MANIFEST,
    business_context,
    company_context_line,
    get_business_profile,
    set_business_profile,
)
from app.venture.workflows import VENTURE_WORKFLOWS, run_intake_review
from tests.fake_anthropic import FakeClient, response, text_block


@pytest.fixture()
def writable_settings(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    return settings


@pytest.fixture()
def writable_engine(writable_settings):
    return make_engine(writable_settings.db_path)


def make_service(settings, routes) -> tuple[AgentService, FakeClient]:
    fake = FakeClient(routes)
    return AgentService(settings, client_factory=lambda: fake), fake


async def _noop_event(event: dict) -> None:
    return None


def _receive_done(ws) -> None:
    while ws.receive_json()["type"] != "done":
        pass


EXPECTED_BUSINESS_KEYS = {
    "name",
    "description_own_words",
    "founded",
    "situation_own_words",
    "decision_pending",
    "biggest_worries",
    "customers_who",
    "why_customers_buy",
    "customer_count",
    "revenue_monthly",
    "pricing_summary",
    "costs_summary",
    "margins_estimate",
    "team",
    "tools_systems",
    "process_pain",
    "sales_channels",
    "marketing_summary",
    "cac_knowledge",
    "competitors",
    "differentiation",
    "goals_12mo",
    "constraints",
    "avoid",
}

LEGACY_PROMPT_HASHES = {
    "FPA": "7f33f648031757b4437b3bf814e545862c4fe1a0e50450bbb2555650928e84f0",
    "REPORTING": "5122ad07e850182f880cf3992825d1d998ab591f8c338c55b821138ef64464e1",
    "REVENUE": "52375ab4b203fdc7ae556a3478fbefd1f3cbbbf1beed9249372345f9636a7dae",
    "CONTROL": "c68c9b20e12f835606654e61b85b67cb62de4c282a01f1516052175ba1835ac2",
    "CFO": "d929c31c1d058ff745af6b2c8e43cf367453b68c269b5d45ad13b9bbee3ef55b",
    "CONTENT": "f19fbd16ad23481829f5a50fcd6311d46ec7ca4319fd4b528d271c658a5c2ee3",
    "CMO": "9fd6314697ec67f9429cbcfe1b3d988c60ec42e7d2ec58f0738bd7f903d1066b",
    "CTO": "5bcbc327469700406b23d7f6f39ced729817aa3679c40073bc3fcbcb2892eeb2",
    "RESEARCHER": "bd2bc2f1ebf2e6a6a1f88908e1903038926f36fe7108e7cfbad20e618fd2ba9a",
    "COORDINATOR": "2a147a762795537d7b42f0e2779995f8fae59e5f2ead4db3aab5087b1f37cc77",
    "CEO": "097305e5846aa705dfff8c699e7c91705a75654ae9f5f67f4f5b247a62813cfe",
}


def test_intake_question_integrity_and_marker_safety():
    keys = [question["key"] for question in INTAKE_QUESTIONS]
    assert keys == list(BUSINESS_KEYS)
    assert len(keys) == len(set(keys))
    assert set(keys) == EXPECTED_BUSINESS_KEYS

    by_key = {question["key"]: question for question in INTAKE_QUESTIONS}
    for key in ("description_own_words", "situation_own_words"):
        assert by_key[key]["required"] is True
        assert "own words" in by_key[key]["question"].lower()

    allowed_types = {"short", "long", "number", "choice"}
    for question in INTAKE_QUESTIONS:
        assert question["section"].strip()
        assert question["why"].strip()
        assert question["type"] in allowed_types
        assert isinstance(question["required"], bool)
        if question["type"] == "choice":
            assert question.get("choices")

    assert {item["key"] for item in UPLOAD_MANIFEST} == {
        "transactions_csv",
        "customers_csv",
        "invoices_csv",
        "context_docs",
    }
    intake_source = inspect.getsource(intake_module)
    collisions = [marker for marker, _ in _MARKERS if marker in intake_source]
    assert collisions == []


def test_business_profile_roundtrip_caps_and_context(writable_engine):
    empty = get_business_profile(writable_engine)
    assert set(empty) == set(BUSINESS_KEYS)
    assert all(value == "" for value in empty.values())
    assert business_context(writable_engine) == ""

    narrative = "We sell scheduling help to independent clinics on subscription."
    profile = set_business_profile(
        writable_engine,
        {
            "name": "  Clinic Flow  ",
            "description_own_words": narrative,
        },
    )
    assert profile["name"] == "Clinic Flow"
    assert profile["description_own_words"] == narrative
    assert set(profile) == set(BUSINESS_KEYS)

    context = business_context(writable_engine)
    assert "BUSINESS PROFILE" in context
    assert "Clinic Flow" in context
    assert narrative in context

    capped = set_business_profile(
        writable_engine,
        {
            "name": "n" * 1_501,
            "situation_own_words": "s" * 4_001,
        },
    )
    assert len(capped["name"]) == 1_500
    assert len(capped["situation_own_words"]) == 4_000

    with pytest.raises(ValueError, match="unknown.*business.*keys"):
        set_business_profile(writable_engine, {"secret_strategy": "nope"})


def test_operations_prompts_are_byte_identical_without_a_profile(writable_settings):
    service = AgentService(writable_settings, client_factory=lambda: None)
    actual_prompts = {
        "FPA": service.finance_team["fpa"].config.system_prompt,
        "REPORTING": service.finance_team["reporting"].config.system_prompt,
        "REVENUE": service.finance_team["revenue"].config.system_prompt,
        "CONTROL": service.finance_team["control"].config.system_prompt,
        "CFO": service.specialists["cfo"].config.system_prompt,
        "CONTENT": service.content_team["content"].config.system_prompt,
        "CMO": service.specialists["cmo"].config.system_prompt,
        "CTO": service.specialists["cto"].config.system_prompt,
        "RESEARCHER": service.specialists["researcher"].config.system_prompt,
        "COORDINATOR": service.specialists["coordinator"].config.system_prompt,
        "CEO": service.ceo.config.system_prompt,
    }

    for name, expected_hash in LEGACY_PROMPT_HASHES.items():
        legacy = getattr(service_module, f"{name}_SYSTEM_PROMPT")
        builder = getattr(service_module, f"build_{name.lower()}_prompt")
        assert hashlib.sha256(legacy.encode()).hexdigest() == expected_hash
        assert builder(DEFAULT_COMPANY_CONTEXT) == legacy
        assert actual_prompts[name] == legacy


def test_operations_prompts_use_the_saved_business_identity(writable_settings):
    service_before = AgentService(writable_settings, client_factory=lambda: None)
    set_business_profile(
        make_engine(writable_settings.db_path),
        {
            "name": "Weekend Kitchens",
            "description_own_words": "We rent licensed kitchens by the hour.",
        },
    )

    service = AgentService(writable_settings, client_factory=lambda: None)
    assert service_before.ceo.config.system_prompt == service_module.CEO_SYSTEM_PROMPT
    expected = "Weekend Kitchens. We rent licensed kitchens by the hour."
    assert service.company_context == expected
    operations_agents = (
        *service.finance_team.values(),
        *service.specialists.values(),
        *service.content_team.values(),
        service.ceo,
    )
    for agent in operations_agents:
        assert expected in agent.config.system_prompt
        assert "Lumina Labs" not in agent.config.system_prompt


def test_service_construction_falls_back_when_context_lookup_fails(
    writable_settings, monkeypatch
):
    def broken_context(engine):
        raise RuntimeError("database locked")

    monkeypatch.setattr(service_module, "company_context_line", broken_context)
    service = AgentService(writable_settings, client_factory=lambda: None)
    assert service.company_context == DEFAULT_COMPANY_CONTEXT
    assert service.ceo.config.system_prompt == service_module.CEO_SYSTEM_PROMPT


def test_company_context_line_fallback_sanitization_and_cap(
    writable_engine, monkeypatch
):
    assert company_context_line(writable_engine) == DEFAULT_COMPANY_CONTEXT

    set_business_profile(
        writable_engine,
        {
            "name": "",
            "description_own_words": "This must be ignored without a name.",
            "pricing_summary": "$10 per month",
        },
    )
    assert company_context_line(writable_engine) == DEFAULT_COMPANY_CONTEXT

    set_business_profile(
        writable_engine,
        {
            "name": "  North\nStar  ",
            "description_own_words": (
                "We help field teams\nclose reports quickly. "
                "Second sentence should not be copied. "
                + "x" * 500
            ),
        },
    )
    context = company_context_line(writable_engine)
    assert context == "North Star. We help field teams close reports quickly."
    assert "\n" not in context
    assert len(context) <= 300

    set_business_profile(
        writable_engine,
        {
            "name": "Simple Pricing",
            "description_own_words": "",
            "pricing_summary": "$49 per month",
        },
    )
    assert company_context_line(writable_engine) == "Simple Pricing. $49 per month."

    set_business_profile(
        writable_engine,
        {
            "name": "Punctuation Description",
            "description_own_words": "...",
            "pricing_summary": "$99 per month",
        },
    )
    assert company_context_line(writable_engine) == "Punctuation Description."

    set_business_profile(
        writable_engine,
        {
            "name": "Bounded Detail",
            "description_own_words": "word " * 100,
        },
    )
    bounded = company_context_line(writable_engine)
    detail = bounded[len("Bounded Detail. ") : -1]
    assert 0 < len(detail) <= 200

    set_business_profile(
        writable_engine,
        {
            "name": "N" * 280,
            "description_own_words": "A description that forces the total over the cap.",
        },
    )
    capped = company_context_line(writable_engine)
    assert len(capped) == 300
    assert capped.endswith(".")

    monkeypatch.setattr(
        intake_module,
        "get_business_profile",
        lambda engine: (_ for _ in ()).throw(RuntimeError("database locked")),
    )
    assert company_context_line(writable_engine) == DEFAULT_COMPANY_CONTEXT


def test_business_and_questions_api_contract(writable_settings):
    service, _ = make_service(writable_settings, [])
    with TestClient(create_app(writable_settings, service)) as client:
        questions = client.get("/api/intake/questions")
        assert questions.status_code == 200
        payload = questions.json()
        assert payload["questions"] == INTAKE_QUESTIONS
        assert payload["uploads"] == UPLOAD_MANIFEST
        assert payload["sections"] == list(
            dict.fromkeys(question["section"] for question in INTAKE_QUESTIONS)
        )

        saved = client.put(
            "/api/business",
            json={
                "values": {
                    "name": "Field Notes",
                    "description_own_words": "We turn site notes into client reports.",
                }
            },
        )
        assert saved.status_code == 200
        assert saved.json()["name"] == "Field Notes"
        assert client.get("/api/business").json() == saved.json()

        unknown = client.put(
            "/api/business", json={"values": {"not_a_business_key": "x"}}
        )
        assert unknown.status_code == 400


async def test_ask_ceo_empty_business_profile_is_an_exact_noop(writable_settings):
    service, fake = make_service(
        writable_settings,
        [response([text_block("Plain response.")])],
    )
    assert business_context(service.engine) == ""
    original = "Give me the next action -- exactly as written."
    history = [
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
    ]

    result, _ = await service.ask_ceo(
        original, on_event=_noop_event, history=history
    )

    assert result.error is None
    assert fake.calls[0]["messages"] == [
        *history,
        {"role": "user", "content": original},
    ]


def test_chat_context_is_injected_but_history_keeps_original_message(
    writable_settings,
):
    engine = make_engine(writable_settings.db_path)
    set_business_profile(
        engine,
        {
            "name": "Weekend Kitchens",
            "description_own_words": "We rent licensed kitchens by the hour.",
        },
    )
    service, fake = make_service(
        writable_settings,
        [
            response([text_block("First answer.")]),
            response([text_block("Second answer.")]),
        ],
    )
    app = create_app(writable_settings, service)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "First original question"})
            _receive_done(ws)
            ws.send_json({"message": "Second original question"})
            _receive_done(ws)

    context = business_context(engine)
    prefix = (
        "BUSINESS CONTEXT (the real company this chat is about):\n"
        f"{context}\n\nREQUEST: "
    )
    first_messages = fake.calls[0]["messages"]
    second_messages = fake.calls[1]["messages"]
    assert first_messages == [
        {"role": "user", "content": prefix + "First original question"}
    ]
    assert second_messages[:2] == [
        {"role": "user", "content": "First original question"},
        {"role": "assistant", "content": "First answer."},
    ]
    assert second_messages[-1] == {
        "role": "user",
        "content": prefix + "Second original question",
    }


def test_intake_text_upload_creates_a_sanitized_report(writable_settings):
    service, _ = make_service(writable_settings, [])
    app = create_app(writable_settings, service)

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/intake/upload",
            data={"kind": "context_docs"},
            files={
                "file": (
                    "../plan.md",
                    b"# Plan\n\nThe pilot is constrained by weekend capacity.",
                    "text/markdown",
                )
            },
        )

    assert uploaded.status_code == 200
    assert uploaded.json()["stored"] is True
    summaries = list_reports(app.state.engine, kind="intake")
    assert len(summaries) == 1
    report = get_report(app.state.engine, summaries[0]["id"])
    assert report["agent"] == "human"
    assert report["title"] == "Intake document: plan.md"
    assert "weekend capacity" in report["content"]
    assert ".." not in report["title"]


def test_intake_csv_upload_stages_file_and_returns_next_step(writable_settings):
    service, _ = make_service(writable_settings, [])
    app = create_app(writable_settings, service)
    csv_content = b"date,amount,kind,category,description\n2026-01-01,10,revenue,sale,One\n"

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/intake/upload",
            data={"kind": "transactions_csv"},
            files={"file": ("transactions.csv", csv_content, "text/csv")},
        )

    assert uploaded.status_code == 200
    payload = uploaded.json()
    assert payload["stored"] is True
    assert "scripts/import_real.py" in payload["next"]
    assert "--source" in payload["next"] and "--check" in payload["next"]

    imports_dir = writable_settings.db_path.parent / "imports"
    staged = list(imports_dir.glob("*.csv"))
    assert len(staged) == 1
    assert staged[0].parent == imports_dir
    assert staged[0].name == "transactions.csv"
    assert staged[0].read_bytes() == csv_content


def test_intake_upload_rejects_unknown_extension_size_and_kind(writable_settings):
    service, _ = make_service(writable_settings, [])
    app = create_app(writable_settings, service)
    oversized = b"x" * (2 * 1024 * 1024 + 1)

    with TestClient(app) as client:
        bad_extension = client.post(
            "/api/intake/upload",
            data={"kind": "context_docs"},
            files={"file": ("plan.pdf", b"pdf", "application/pdf")},
        )
        too_large = client.post(
            "/api/intake/upload",
            data={"kind": "context_docs"},
            files={"file": ("large.txt", oversized, "text/plain")},
        )
        unknown_kind = client.post(
            "/api/intake/upload",
            data={"kind": "mystery"},
            files={"file": ("data.csv", b"a,b\n1,2\n", "text/csv")},
        )
        invalid_text = client.post(
            "/api/intake/upload",
            data={"kind": "context_docs"},
            files={"file": ("notes.md", b"\xff\xfe", "text/markdown")},
        )

    assert bad_extension.status_code == 400
    assert too_large.status_code == 400
    assert unknown_kind.status_code == 400
    assert invalid_text.status_code == 400


async def test_intake_review_saves_three_sections_and_three_memories(
    writable_settings, writable_engine
):
    business_name = "Weekend Kitchens"
    narrative = "We rent licensed kitchens by the hour to food founders."
    set_business_profile(
        writable_engine,
        {
            "name": business_name,
            "description_own_words": narrative,
            "revenue_monthly": "$12k-$15k",
        },
    )
    save_report(
        writable_engine,
        title="Intake document: operating-note.md",
        content="The pilot is currently constrained by weekend capacity.",
        agent="human",
        kind="intake",
    )
    outputs = {
        "financial skeptic": "CFO learned that cash collection timing is unclear.",
        "demand skeptic": "CMO learned that food founders are the core segment.",
        "Risk Officer agent": "Risk learned that kitchen licensing needs validation.",
    }
    service, fake = make_service(
        writable_settings,
        {
            marker: [response([text_block(output)])]
            for marker, output in outputs.items()
        },
    )

    report_id = await run_intake_review(
        service, writable_engine, "This submitted topic must be ignored"
    )

    report = get_report(writable_engine, report_id)
    assert report["kind"] == "intake"
    assert report["agent"] == "coo"
    assert report["title"] == f"Business intake review: {business_name}"
    for output in outputs.values():
        assert output in report["content"]
    headings = [
        line.lower() for line in report["content"].splitlines() if line.startswith("## ")
    ]
    assert any("cfo" in heading or "financial" in heading for heading in headings)
    assert any("cmo" in heading or "customer" in heading for heading in headings)
    assert any("risk" in heading for heading in headings)

    memories = list_memories(writable_engine, related_idea=business_name)
    assert {memory["category"] for memory in memories} == {
        "financial_assumption",
        "customer_research",
        "risk",
    }
    assert len(memories) == 3
    for memory in memories:
        assert memory["content"].endswith(f"Full report: #{report_id}.")

    assert len(fake.calls) == 3
    for call in fake.calls:
        task = call["messages"][0]["content"]
        assert task.startswith(f"TOPIC: {business_name}\n")
        assert narrative in task
        assert "weekend capacity" in task
        for required in (
            "What I learned",
            "Assumptions to validate",
            "Red flags",
        ):
            assert required in task

    workflow = VENTURE_WORKFLOWS["intake_review"]
    assert workflow["label"] == "Business intake review"
    description = workflow["description"].lower()
    assert "business" in description and "topic" in description
