"""Guardrail tests for the SELECT-only sql_query tool."""
from __future__ import annotations

import pytest

from app.agents.service import FINANCE_TABLES
from app.tools.base import ToolError
from app.tools.sql_query import run_sql_query

ALLOW = frozenset(FINANCE_TABLES)


def q(seeded_db, query, **kw):
    db_path, _ = seeded_db
    return run_sql_query(query, db_path=db_path, allowed_tables=ALLOW, **kw)


def test_simple_select(seeded_db):
    res = q(seeded_db, "SELECT COUNT(*) AS n FROM customers")
    assert res["columns"] == ["n"]
    assert res["rows"][0][0] > 0


def test_join_and_cte_allowed(seeded_db):
    res = q(
        seeded_db,
        """
        WITH monthly AS (
          SELECT strftime('%Y-%m', date) AS m, SUM(amount) AS rev
          FROM transactions WHERE type = 'revenue' GROUP BY m
        )
        SELECT m, rev FROM monthly ORDER BY m DESC LIMIT 3
        """,
    )
    assert res["row_count"] == 3


def test_insert_rejected(seeded_db):
    with pytest.raises(ToolError, match="Only SELECT"):
        q(seeded_db, "INSERT INTO customers (name) VALUES ('Evil Co')")


@pytest.mark.parametrize(
    "stmt",
    [
        "UPDATE customers SET mrr = 0",
        "DELETE FROM transactions",
        "DROP TABLE customers",
        "PRAGMA writable_schema = 1",
        "ATTACH DATABASE '/tmp/x.db' AS x",
        "CREATE TABLE pwned (id INT)",
    ],
)
def test_writes_and_admin_rejected(seeded_db, stmt):
    with pytest.raises(ToolError):
        q(seeded_db, stmt)


def test_write_hidden_behind_cte_rejected(seeded_db):
    # Passes the cheap prefix check; must be stopped by the authorizer/read-only conn.
    with pytest.raises(ToolError):
        q(seeded_db, "WITH x AS (SELECT 1) INSERT INTO tasks (title) SELECT * FROM x")


def test_table_allowlist_enforced(seeded_db):
    with pytest.raises(ToolError, match="allowlist"):
        q(seeded_db, "SELECT * FROM tasks")  # tasks is not a finance table
    with pytest.raises(ToolError, match="allowlist"):
        q(seeded_db, "SELECT sql FROM sqlite_master")


def test_multiple_statements_rejected(seeded_db):
    with pytest.raises(ToolError, match="single SQL statement"):
        q(seeded_db, "SELECT 1; SELECT 2")


def test_row_limit_truncates(seeded_db):
    res = q(seeded_db, "SELECT id FROM transactions", row_limit=5)
    assert res["row_count"] == 5
    assert res["truncated"] is True


def test_leading_comment_ok(seeded_db):
    res = q(seeded_db, "-- monthly revenue\nSELECT COUNT(*) FROM invoices")
    assert res["rows"][0][0] > 0
