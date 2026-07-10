"""Deterministic KPI queries for the Overview page (no LLM involved)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def get_meta(engine: Engine) -> dict[str, str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT key, value FROM meta")).all()
    return {k: v for k, v in rows}


def get_monthly_series(engine: Engine) -> list[dict]:
    sql = text(
        """
        SELECT strftime('%Y-%m', date) AS month,
               ROUND(SUM(CASE WHEN type = 'revenue' THEN amount ELSE 0 END), 2) AS revenue,
               ROUND(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 2) AS expenses
        FROM transactions
        GROUP BY month
        ORDER BY month
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
    return [
        {
            "month": m,
            "revenue": rev or 0.0,
            "expenses": exp or 0.0,
            "profit": round((rev or 0.0) - (exp or 0.0), 2),
        }
        for m, rev, exp in rows
    ]


def get_kpis(engine: Engine) -> dict:
    meta = get_meta(engine)
    series = get_monthly_series(engine)
    starting_cash = float(meta.get("starting_cash", 0))

    total_revenue = sum(m["revenue"] for m in series)
    total_expenses = sum(m["expenses"] for m in series)
    cash = round(starting_cash + total_revenue - total_expenses, 2)

    last = series[-1] if series else {"month": None, "revenue": 0, "expenses": 0, "profit": 0}
    last3 = series[-3:] if len(series) >= 3 else series
    avg_burn = (
        round(sum(m["expenses"] - m["revenue"] for m in last3) / len(last3), 2) if last3 else 0.0
    )
    runway_months = round(cash / avg_burn, 1) if avg_burn > 0 else None

    with engine.connect() as conn:
        mrr, active_customers = conn.execute(
            text(
                "SELECT COALESCE(SUM(mrr), 0), COUNT(*) "
                "FROM customers WHERE churn_date IS NULL"
            )
        ).one()
        open_tasks = conn.execute(
            text("SELECT COUNT(*) FROM tasks WHERE status != 'done'")
        ).scalar_one()

    prev = series[-2] if len(series) >= 2 else None
    mrr_from_revenue = last["revenue"]
    revenue_mom = (
        round((last["revenue"] - prev["revenue"]) / prev["revenue"] * 100, 1)
        if prev and prev["revenue"]
        else None
    )

    return {
        "company": meta.get("company", "—"),
        "window_start": meta.get("window_start"),
        "window_end": meta.get("window_end"),
        "mrr": round(float(mrr), 2),
        "mrr_billed_last_month": mrr_from_revenue,
        "active_customers": int(active_customers),
        "cash": cash,
        "avg_monthly_burn": avg_burn,
        "runway_months": runway_months,
        "open_tasks": int(open_tasks),
        "last_month": last["month"],
        "last_month_revenue": last["revenue"],
        "last_month_expenses": last["expenses"],
        "last_month_profit": last["profit"],
        "revenue_mom_pct": revenue_mom,
    }
