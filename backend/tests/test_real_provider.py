"""Contract tests for importing real-company CSV snapshots safely."""
from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.api.kpis import get_kpis
from app.data.real import RealBusinessProvider
from app.db import make_engine
from app.models import (
    Approval,
    Base,
    Campaign,
    Customer,
    Employee,
    EvalResult,
    FounderProfile,
    Idea,
    Invoice,
    Memory,
    Meta,
    Project,
    Report,
    Task,
    Transaction,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "real_csv"
BUSINESS_MODELS = (Invoice, Transaction, Task, Project, Campaign, Customer, Employee, Meta)
ARTIFACT_MODELS = (Approval, Report, FounderProfile, Memory, Idea, EvalResult)


def _copy_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    shutil.copytree(FIXTURE_DIR, source)
    return source


def _engine(tmp_path: Path):
    return make_engine(tmp_path / "real.db")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _change_row(path: Path, row_index: int, **changes: str) -> None:
    fieldnames, rows = _read_csv(path)
    rows[row_index].update(changes)
    _write_csv(path, fieldnames, rows)


def _table_counts(engine, models=BUSINESS_MODELS) -> dict[str, int]:
    schema = inspect(engine)
    counts: dict[str, int] = {}
    with Session(engine) as session:
        for model in models:
            if schema.has_table(model.__tablename__):
                counts[model.__tablename__] = session.scalar(
                    select(func.count()).select_from(model)
                )
            else:
                counts[model.__tablename__] = 0
    return counts


def _validation_message(provider: RealBusinessProvider, engine) -> str:
    with pytest.raises(ValueError) as exc_info:
        provider.provision(engine)
    return str(exc_info.value)


def test_happy_import_has_expected_rows_meta_and_positive_kpis(tmp_path):
    engine = _engine(tmp_path)
    summary = RealBusinessProvider(FIXTURE_DIR).provision(engine)

    expected = {
        "customers": 6,
        "employees": 2,
        "campaigns": 2,
        "projects": 2,
        "tasks": 3,
        "transactions": 18,
        "invoices": 10,
    }
    assert {name: summary["tables"][name] for name in expected} == expected
    assert summary["window"] == ["2025-01-01", "2025-02-28"]
    assert summary["warnings"] == []

    with Session(engine) as session:
        meta = {row.key: row.value for row in session.scalars(select(Meta)).all()}
    assert meta["company"] == "Fixture Works"
    assert meta["starting_cash"] == "100000.00"
    assert meta["window_start"] == "2025-01-01"
    assert meta["window_end"] == "2025-02-28"
    assert dt.datetime.fromisoformat(meta["generated_at"])
    assert summary["tables"]["meta"] == len(meta)

    kpis = get_kpis(engine)
    assert kpis["active_customers"] == 5
    assert kpis["mrr"] == 1000.0
    assert kpis["last_month_revenue"] == 1000.0
    assert kpis["cash"] > 0
    assert kpis["avg_monthly_burn"] > 0


def test_required_file_must_exist_and_failure_writes_no_rows(tmp_path):
    source = _copy_source(tmp_path)
    (source / "transactions.csv").unlink()
    engine = _engine(tmp_path)

    message = _validation_message(RealBusinessProvider(source), engine)

    assert "transactions.csv:0" in message
    assert re.search(r"required|missing", message, re.IGNORECASE)
    assert not any(_table_counts(engine).values())


def test_headers_reject_unknown_and_missing_columns_before_row_import(tmp_path):
    source = _copy_source(tmp_path)
    path = source / "transactions.csv"
    contents = path.read_text(encoding="utf-8")
    path.write_text(contents.replace("amount", "total", 1), encoding="utf-8")
    engine = _engine(tmp_path)

    message = _validation_message(RealBusinessProvider(source), engine)

    assert "transactions.csv:1" in message
    assert "amount" in message
    assert "total" in message
    assert not any(_table_counts(engine).values())


def test_headers_are_case_insensitive_and_order_independent(tmp_path):
    source = _copy_source(tmp_path)
    path = source / "meta.csv"
    _, rows = _read_csv(path)
    reordered = [{"VALUE": row["value"], "KEY": row["key"]} for row in rows]
    _write_csv(path, ["VALUE", "KEY"], reordered)

    summary = RealBusinessProvider(source).provision(_engine(tmp_path))

    assert summary["tables"]["customers"] == 6


def test_utf8_bom_and_case_insensitive_foreign_key_names_are_supported(tmp_path):
    source = _copy_source(tmp_path)
    meta_path = source / "meta.csv"
    meta_path.write_text("\ufeff" + meta_path.read_text(encoding="utf-8"), encoding="utf-8")
    _change_row(source / "transactions.csv", 0, customer_name="acme co")
    _change_row(source / "invoices.csv", 0, customer_name="ACME CO")

    summary = RealBusinessProvider(source).provision(_engine(tmp_path))

    assert summary["tables"]["transactions"] == 18


def test_invalid_enum_reports_the_source_line(tmp_path):
    source = _copy_source(tmp_path)
    _change_row(source / "transactions.csv", 0, type="credit")

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "transactions.csv:2" in message
    assert "credit" in message
    assert re.search(r"type|revenue|expense", message, re.IGNORECASE)


def test_starting_cash_meta_key_is_required(tmp_path):
    source = _copy_source(tmp_path)
    path = source / "meta.csv"
    fields, rows = _read_csv(path)
    _write_csv(path, fields, [row for row in rows if row["key"] != "starting_cash"])

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "meta.csv:" in message
    assert "starting_cash" in message


def test_invoice_without_matching_revenue_transaction_is_rejected(tmp_path):
    source = _copy_source(tmp_path)
    _change_row(source / "invoices.csv", 0, amount="999.00")

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "invoices.csv:2" in message
    assert re.search(r"unmatched|no match|matching transaction", message, re.IGNORECASE)


def test_invoice_with_two_matching_transactions_is_rejected_as_ambiguous(tmp_path):
    source = _copy_source(tmp_path)
    path = source / "transactions.csv"
    fields, rows = _read_csv(path)
    rows.append(dict(rows[0]))
    _write_csv(path, fields, rows)

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "invoices.csv:2" in message
    assert re.search(r"ambiguous|multiple|more than one", message, re.IGNORECASE)


def test_invoice_amount_tolerance_is_inclusive_and_transactions_cannot_be_reused(tmp_path):
    source = _copy_source(tmp_path)
    _change_row(source / "invoices.csv", 0, amount="100.01")
    assert RealBusinessProvider(source).provision(_engine(tmp_path))["tables"]["invoices"] == 10

    second_source = _copy_source(tmp_path / "reuse")
    path = second_source / "invoices.csv"
    fields, rows = _read_csv(path)
    rows.append(dict(rows[0]))
    _write_csv(path, fields, rows)

    message = _validation_message(
        RealBusinessProvider(second_source),
        make_engine(tmp_path / "reuse.db"),
    )
    assert re.search(r"already matched|already.*invoice|reuse", message, re.IGNORECASE)


def test_unknown_foreign_key_name_reports_its_transaction_line(tmp_path):
    source = _copy_source(tmp_path)
    _change_row(source / "transactions.csv", 0, customer_name="Missing Customer")

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "transactions.csv:2" in message
    assert "Missing Customer" in message
    assert re.search(r"customer|foreign|unknown", message, re.IGNORECASE)


def test_absent_optional_files_import_empty_tables_and_return_warnings(tmp_path):
    source = _copy_source(tmp_path)
    optional = ["invoices", "campaigns", "projects", "employees", "tasks"]
    for stem in optional:
        (source / f"{stem}.csv").unlink()
    path = source / "transactions.csv"
    fields, rows = _read_csv(path)
    for row in rows:
        row["employee_name"] = ""
        row["campaign_name"] = ""
    _write_csv(path, fields, rows)

    summary = RealBusinessProvider(source).provision(_engine(tmp_path))

    for stem in optional:
        assert summary["tables"][stem] == 0
        assert stem in "\n".join(summary["warnings"]).lower()


def test_artifact_only_database_can_import_without_force(tmp_path):
    engine = _engine(tmp_path)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            Report(
                title="Existing artifact",
                kind="report",
                agent="cfo",
                created_at=dt.datetime(2025, 3, 1, 12, 0),
                content="kept",
            )
        )
        session.commit()

    summary = RealBusinessProvider(FIXTURE_DIR).provision(engine)

    assert summary["tables"]["customers"] == 6
    assert _table_counts(engine, (Report,)) == {"reports": 1}


def test_any_existing_business_row_requires_force_even_without_generated_meta(tmp_path):
    engine = _engine(tmp_path)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            Customer(
                name="Existing Customer",
                plan="starter",
                mrr=10.0,
                signup_date=dt.date(2025, 1, 1),
                churn_date=None,
            )
        )
        session.commit()

    with pytest.raises(ValueError, match="force"):
        RealBusinessProvider(FIXTURE_DIR).provision(engine)

    assert _table_counts(engine)["customers"] == 1


def test_provision_refuses_existing_business_data_and_force_preserves_artifacts(tmp_path):
    engine = _engine(tmp_path)
    provider = RealBusinessProvider(FIXTURE_DIR)
    provider.provision(engine)
    now = dt.datetime(2025, 3, 1, 12, 0)
    with Session(engine) as session:
        session.add_all(
            [
                Approval(kind="content", title="Approval", channel="web", agent="cmo", status="pending", content="draft", created_at=now),
                Report(title="Report", kind="report", agent="cfo", created_at=now, content="kept"),
                FounderProfile(key="constraints", value="kept", updated_at=now),
                Memory(category="decision", title="Memory", content="kept", source_agent="ceo", status="active", created_at=now, updated_at=now),
                Idea(title="Idea", description="kept", scores_json="{}", total_score=5.0, verdict="test_first", best_version="best", worst_risk="risk", validation_test="test", next_actions="- act", created_at=now),
                EvalResult(case_id="fixture", agent="ceo", model="candidate", score=8.0, passed=True, details_json="{}", created_at=now),
            ]
        )
        session.commit()
    artifacts_before = _table_counts(engine, ARTIFACT_MODELS)
    business_before = _table_counts(engine)

    with pytest.raises(ValueError, match="force"):
        provider.provision(engine)
    assert _table_counts(engine, ARTIFACT_MODELS) == artifacts_before
    assert _table_counts(engine) == business_before

    provider.provision(engine, force=True)
    assert _table_counts(engine, ARTIFACT_MODELS) == artifacts_before
    assert all(count == 1 for count in artifacts_before.values())


def test_invalid_forced_replacement_leaves_existing_business_rows_intact(tmp_path):
    engine = _engine(tmp_path)
    RealBusinessProvider(FIXTURE_DIR).provision(engine)
    counts_before = _table_counts(engine)
    with Session(engine) as session:
        meta_before = {row.key: row.value for row in session.scalars(select(Meta)).all()}

    source = _copy_source(tmp_path)
    _change_row(source / "transactions.csv", 0, customer_name="Missing Customer")
    with pytest.raises(ValueError):
        RealBusinessProvider(source).provision(engine, force=True)

    assert _table_counts(engine) == counts_before
    with Session(engine) as session:
        meta_after = {row.key: row.value for row in session.scalars(select(Meta)).all()}
    assert meta_after == meta_before


def test_check_returns_ok_reconciliation_and_writes_nothing(tmp_path):
    engine = _engine(tmp_path)
    Base.metadata.create_all(engine)
    before = _table_counts(engine, BUSINESS_MODELS + ARTIFACT_MODELS)

    summary = RealBusinessProvider(FIXTURE_DIR).check(engine)

    lines = summary["reconciliation"]
    assert lines
    assert all(line.startswith("[OK]") for line in lines)
    assert any("subscription" in line.lower() for line in lines)
    assert any("payroll" in line.lower() for line in lines)
    assert any("campaign" in line.lower() for line in lines)
    assert _table_counts(engine, BUSINESS_MODELS + ARTIFACT_MODELS) == before


def test_check_does_not_create_a_new_database_file(tmp_path):
    db_path = tmp_path / "dry-run.db"
    engine = make_engine(db_path)

    summary = RealBusinessProvider(FIXTURE_DIR).check(engine)

    assert summary["reconciliation"]
    assert not db_path.exists()


@pytest.mark.parametrize(
    ("filename", "contents", "expected"),
    [
        ("customers.csv", b"name,plan,mrr,signup_date,churn_date\nBad,starter,1,2025-01-01,\xff", "utf"),
        ("meta.csv", b"", "empty|header"),
    ],
)
def test_unreadable_or_empty_csv_is_a_row_zero_error(
    tmp_path, filename: str, contents: bytes, expected: str
):
    source = _copy_source(tmp_path)
    (source / filename).write_bytes(contents)

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert f"{filename}:0" in message
    assert re.search(expected, message, re.IGNORECASE)


def test_present_but_empty_optional_file_is_an_error(tmp_path):
    source = _copy_source(tmp_path)
    (source / "campaigns.csv").write_bytes(b"")

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "campaigns.csv:0" in message
    assert re.search(r"empty|header", message, re.IGNORECASE)


@pytest.mark.parametrize(
    "amount",
    ["1,2", "1_000.00", "1e-400", "1e9999", "NaN", "Infinity"],
)
def test_non_canonical_or_unrepresentable_money_is_rejected(tmp_path, amount):
    source = _copy_source(tmp_path)
    _change_row(source / "transactions.csv", 0, amount=amount)

    message = _validation_message(RealBusinessProvider(source), _engine(tmp_path))

    assert "transactions.csv:2" in message
    assert re.search(r"finite|plain decimal|greater than zero", message, re.IGNORECASE)


def test_starting_cash_with_separators_is_rejected_before_kpi_persistence(tmp_path):
    source = _copy_source(tmp_path)
    _change_row(source / "meta.csv", 1, value="1,000.00")
    engine = _engine(tmp_path)

    message = _validation_message(RealBusinessProvider(source), engine)

    assert "meta.csv:3" in message
    assert "plain decimal" in message
    assert not any(_table_counts(engine).values())


def test_check_warns_about_unlinked_marketing_spend_without_blocking(tmp_path):
    source = _copy_source(tmp_path)
    path = source / "transactions.csv"
    fields, rows = _read_csv(path)
    rows.append(
        {
            "date": "2025-02-20",
            "type": "expense",
            "category": "marketing",
            "amount": "25.00",
            "description": "Unattributed marketing charge",
            "customer_name": "",
            "employee_name": "",
            "campaign_name": "",
        }
    )
    _write_csv(path, fields, rows)

    summary = RealBusinessProvider(source).check()

    assert any(
        line.startswith("[WARN]") and "unlinked marketing" in line
        for line in summary["reconciliation"]
    )


def test_validation_collects_at_most_twenty_errors_and_never_partially_writes(tmp_path):
    source = _copy_source(tmp_path)
    path = source / "customers.csv"
    fields, _ = _read_csv(path)
    rows = [
        {
            "name": f"Broken Customer {index}",
            "plan": "invalid",
            "mrr": "-1",
            "signup_date": "not-a-date",
            "churn_date": "also-not-a-date",
        }
        for index in range(25)
    ]
    _write_csv(path, fields, rows)
    engine = _engine(tmp_path)

    message = _validation_message(RealBusinessProvider(source), engine)

    reported = re.findall(r"customers\.csv:\d+:", message)
    assert 2 <= len(reported) <= 20
    assert not any(_table_counts(engine).values())
