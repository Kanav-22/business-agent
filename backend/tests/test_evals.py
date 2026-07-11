"""V4 deterministic evaluation rubric, corpus, runner, and API surface."""
from __future__ import annotations

import json
import shutil
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.agents.service import AgentService
from app.api.venture import list_eval_results, save_eval_result
from app.db import make_engine
from app.main import create_app
from evals.rubric import score_output
from evals.runner import AGENT_FOR_CASE, CASES_DIR, load_case, load_cases, run_cases


CASE_FILES = sorted(CASES_DIR.glob("*.json"))


@pytest.fixture()
def writable_settings(settings, tmp_path):
    db_copy = tmp_path / "writable.db"
    shutil.copy(settings.db_path, db_copy)
    settings.db_path = db_copy
    settings.demo_mode = True
    return settings


def test_ceo_rubric_scores_good_bad_and_empty_answers():
    case = load_case(CASES_DIR / "ceo_bootstrap_founder.json")
    good = """\
Niche: solo dermatology clinics with one receptionist.
Offer: a done-for-you appointment automation service at ₹10,000 per month.
MVP: a manual pilot using a form, calendar, and human review in 3 days.
Acquisition plan: list 100 prospects, send 20 direct outreach messages, and book
5 discovery calls before building more.
Main risks: patient-data handling and unproven willingness to pay; validate with
3 paid pilots and collect only scheduling data.
7-day plan: Day 1 list clinics; Day 2 contact 20; Day 3 run 5 calls; Day 4 send
the offer; Day 5 close one pilot; Day 7 review the result and stop if nobody pays.
"""
    bad = (
        "Do market research, stay focused, and execute consistently. It depends on "
        "many factors. This game-changing idea could revolutionize the market."
    )

    good_result = score_output(case, good)
    bad_result = score_output(case, bad)
    empty_result = score_output(case, "   ")

    assert good_result["score"] >= case["pass_score"]
    assert bad_result["score"] < 4
    bad_hits = {
        criterion["name"]
        for criterion in bad_result["criteria"]
        if criterion["kind"] == "bad_sign" and criterion["hit"]
    }
    assert {"hype cliché", "hedging non-answer"} <= bad_hits
    assert empty_result["score"] == 0
    assert not empty_result["passed"]
    assert all(not criterion["hit"] for criterion in empty_result["criteria"])


def test_case_corpus_loads_with_two_cases_per_role():
    cases = load_cases()
    counts = Counter(case["agent"] for case in cases)
    assert len(cases) >= 18
    assert set(counts) == set(AGENT_FOR_CASE)
    assert all(count >= 2 for count in counts.values())
    assert len({case["id"] for case in cases}) == len(cases)


@pytest.mark.parametrize("case_path", CASE_FILES, ids=lambda path: path.stem)
def test_case_suggestions_do_not_trivially_pass_their_own_rubric(case_path):
    case = load_case(case_path)
    suggestions = "\n".join(case["improvement_suggestions"])
    assert score_output(case, suggestions)["score"] < case["pass_score"]


def test_invalid_case_reports_its_filename(tmp_path):
    case = load_case(CASES_DIR / "ceo_bootstrap_founder.json")
    case["expected_elements"][0]["pattern"] = "[unterminated"
    path = tmp_path / "broken-case.json"
    path.write_text(json.dumps(case), encoding="utf-8")

    with pytest.raises(ValueError, match="broken-case.json"):
        load_case(path)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_invalid_case_rejects_non_finite_numbers(tmp_path, bad_value):
    case = load_case(CASES_DIR / "ceo_bootstrap_founder.json")
    case["expected_elements"][0]["weight"] = bad_value
    path = tmp_path / "non-finite.json"
    path.write_text(json.dumps(case), encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite.json"):
        load_case(path)


def test_invalid_utf8_case_reports_its_filename(tmp_path):
    path = tmp_path / "invalid-utf8.json"
    path.write_bytes(b"\xff")

    with pytest.raises(ValueError, match="invalid-utf8.json"):
        load_case(path)


@pytest.mark.parametrize(
    ("case_id", "rebuttal", "criterion_name"),
    [
        (
            "board_procurement_pivot",
            "Do not build the entire suite; validate the narrow workflow first.",
            "rubber-stamps full rebuild",
        ),
        (
            "ceo_bootstrap_founder",
            "Do not raise funding before validating demand with paid pilots.",
            "fundraising instead of validation",
        ),
        (
            "cmo_niche_channel",
            "Do not use all channels; start with direct outreach.",
            "multi-channel dilution",
        ),
        (
            "risk_patient_data_compliance",
            "The claim that HIPAA does not apply is false and dangerous.",
            "accepts vendor exemption",
        ),
    ],
)
def test_bad_signs_do_not_penalize_explicit_rebuttals(
    case_id,
    rebuttal,
    criterion_name,
):
    result = score_output(load_case(CASES_DIR / f"{case_id}.json"), rebuttal)
    criterion = next(item for item in result["criteria"] if item["name"] == criterion_name)
    assert not criterion["hit"]


async def test_run_cases_demo_smoke_persists_results(writable_settings):
    service = AgentService(writable_settings)
    engine = make_engine(writable_settings.db_path)
    selected_ids = {"ceo_bootstrap_founder", "cfo_runway_pricing"}
    cases = [case for case in load_cases() if case["id"] in selected_ids]

    results = await run_cases(service, engine, cases)

    assert len(results) == 2
    assert all(
        set(result) == {"case_id", "agent", "score", "passed", "error"}
        for result in results
    )
    assert all(0 <= result["score"] <= 10 for result in results)
    rows = list_eval_results(engine)
    assert len(rows) == 2
    assert {row["case_id"] for row in rows} == selected_ids
    assert all(row["model"] == writable_settings.agent_model for row in rows)


def test_evals_endpoint_returns_persisted_rows(writable_settings):
    engine = make_engine(writable_settings.db_path)
    eval_id = save_eval_result(
        engine,
        case_id="api_eval_case",
        agent="risk",
        model=writable_settings.agent_model,
        score=7.5,
        passed=True,
        details={"criteria": [], "suggestions": [], "error": None},
    )
    service = AgentService(writable_settings)
    app = create_app(settings=writable_settings, service=service)

    with TestClient(app) as client:
        response = client.get("/api/evals?agent=risk")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": eval_id,
            "case_id": "api_eval_case",
            "agent": "risk",
            "model": writable_settings.agent_model,
            "score": 7.5,
            "passed": True,
            "details": {"criteria": [], "suggestions": [], "error": None},
            "created_at": response.json()[0]["created_at"],
        }
    ]
