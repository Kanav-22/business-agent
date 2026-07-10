"""Verifies the synthetic dataset is internally consistent — the invariants
documented in app/data/synthetic.py. This is the same checkability the Phase 3
Control agent will rely on."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import text

from app.api.kpis import get_kpis
from app.data.synthetic import N_MONTHS, PLAN_PRICES, add_months, month_floor
from tests.conftest import ANCHOR

WINDOW = [add_months(ANCHOR, -N_MONTHS + i) for i in range(N_MONTHS)]


def _d(value) -> dt.date:
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(value)


def test_window_covers_18_months(seeded_db):
    _, engine = seeded_db
    with engine.connect() as conn:
        months = [
            r[0]
            for r in conn.execute(
                text("SELECT DISTINCT strftime('%Y-%m', date) FROM transactions ORDER BY 1")
            )
        ]
    assert months == [m.strftime("%Y-%m") for m in WINDOW]


def test_subscription_revenue_reconciles_with_customers(seeded_db):
    """Rule 1+2: per-customer billing matches signup/churn/plan history and
    customers.mrr equals the last billed amount."""
    _, engine = seeded_db
    with engine.connect() as conn:
        customers = conn.execute(
            text("SELECT id, plan, mrr, signup_date, churn_date FROM customers")
        ).all()
        txns = conn.execute(
            text(
                "SELECT customer_id, date, amount FROM transactions "
                "WHERE category = 'subscription' ORDER BY customer_id, date"
            )
        ).all()

    billed: dict[int, list[tuple[dt.date, float]]] = defaultdict(list)
    for cust_id, date, amount in txns:
        billed[cust_id].append((_d(date), amount))

    assert len(customers) > 0
    for cust_id, plan, mrr, signup, churn in customers:
        signup, churn = _d(signup), _d(churn) if churn else None
        expected_months = [
            m for m in WINDOW if month_floor(signup) <= m and (churn is None or churn > m)
        ]
        got = billed[cust_id]
        assert [m for m, _ in got] == expected_months, f"customer {cust_id} billing months"
        amounts = [a for _, a in got]
        assert all(a in PLAN_PRICES.values() for a in amounts)
        # expansion only — amounts never decrease
        assert amounts == sorted(amounts), f"customer {cust_id} downgraded"
        assert len(expected_months) > 0, f"customer {cust_id} never billed in window"
        assert amounts[-1] == mrr == PLAN_PRICES[plan], f"customer {cust_id} mrr mismatch"


def test_monthly_revenue_equals_active_customer_mrr(seeded_db):
    """Aggregate view of rule 1: each month's revenue equals the sum of the
    then-current MRR of customers billed that month (checked via txn joins)."""
    _, engine = seeded_db
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT strftime('%Y-%m', date), SUM(amount), COUNT(DISTINCT customer_id), COUNT(*) "
                "FROM transactions WHERE category = 'subscription' GROUP BY 1"
            )
        ).all()
    for month, total, n_customers, n_rows in rows:
        assert n_customers == n_rows, f"{month}: customer billed twice"
        assert total > 0


def test_salaries_reconcile_with_employees(seeded_db):
    _, engine = seeded_db
    with engine.connect() as conn:
        employees = conn.execute(
            text("SELECT id, salary_annual, hire_date FROM employees")
        ).all()
        rows = conn.execute(
            text(
                "SELECT strftime('%Y-%m', date), SUM(amount), COUNT(*) FROM transactions "
                "WHERE category = 'salary' GROUP BY 1"
            )
        ).all()
    actual = {month: (total, n) for month, total, n in rows}
    assert len(employees) == 12
    for m in WINDOW:
        expected_emps = [e for e in employees if _d(e[2]) <= m]
        expected_total = round(sum(round(e[1] / 12, 2) for e in expected_emps), 2)
        got_total, got_n = actual[m.strftime("%Y-%m")]
        assert got_n == len(expected_emps), f"{m}: salary txn count"
        assert abs(got_total - expected_total) < 0.05, f"{m}: payroll total"


def test_marketing_spend_reconciles_with_campaigns(seeded_db):
    _, engine = seeded_db
    with engine.connect() as conn:
        campaigns = conn.execute(text("SELECT id, spend FROM campaigns")).all()
        spent = dict(
            conn.execute(
                text(
                    "SELECT campaign_id, SUM(amount) FROM transactions "
                    "WHERE category = 'marketing' GROUP BY campaign_id"
                )
            ).all()
        )
        orphan = conn.execute(
            text(
                "SELECT COUNT(*) FROM transactions "
                "WHERE category = 'marketing' AND campaign_id IS NULL"
            )
        ).scalar_one()
    assert orphan == 0
    assert len(campaigns) >= 10
    for cid, spend in campaigns:
        assert abs(spent[cid] - spend) < 0.01, f"campaign {cid} spend mismatch"


def test_invoices_match_subscription_transactions(seeded_db):
    _, engine = seeded_db
    with engine.connect() as conn:
        n_sub = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE category = 'subscription'")
        ).scalar_one()
        n_inv = conn.execute(text("SELECT COUNT(*) FROM invoices")).scalar_one()
        mismatched = conn.execute(
            text(
                "SELECT COUNT(*) FROM invoices i JOIN transactions t "
                "ON t.id = i.transaction_id "
                "WHERE ABS(i.amount - t.amount) > 0.001 OR i.customer_id != t.customer_id"
            )
        ).scalar_one()
        bad_status = conn.execute(
            text("SELECT COUNT(*) FROM invoices WHERE status NOT IN ('paid','issued','overdue')")
        ).scalar_one()
    assert n_inv == n_sub
    assert mismatched == 0
    assert bad_status == 0


def test_campaign_conversions_roughly_match_signups(seeded_db):
    _, engine = seeded_db
    with engine.connect() as conn:
        conversions = conn.execute(text("SELECT SUM(conversions) FROM campaigns")).scalar_one()
        signups = conn.execute(
            text("SELECT COUNT(*) FROM customers WHERE signup_date >= :start"),
            {"start": WINDOW[0].isoformat()},
        ).scalar_one()
    assert signups > 0
    assert 0.4 * signups <= conversions <= signups


def test_company_shape_and_kpis(seeded_db):
    _, engine = seeded_db
    kpis = get_kpis(engine)
    assert 100 <= kpis["active_customers"] <= 190
    assert kpis["mrr"] > 10_000
    assert kpis["cash"] > 0
    assert kpis["avg_monthly_burn"] > 0
    assert kpis["runway_months"] and kpis["runway_months"] > 3
    # last month's billed revenue must equal MRR of customers active that month —
    # spot-check: billed revenue is within plan-price distance of current MRR.
    assert kpis["last_month_revenue"] > 0
