"""SELECT-only SQL tool with a per-agent table allowlist and row limit.

Enforcement is layered — none of it relies on the model behaving:
1. The connection is opened read-only (sqlite URI mode=ro).
2. A sqlite authorizer callback denies every operation except SELECT/READ
   (on allowlisted tables), scalar functions, and recursive CTEs.
3. sqlite3.Connection.execute refuses multi-statement strings outright.
4. A cheap prefix check gives the agent a friendlier error before any of
   the above trips.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from app.tools.base import Tool, ToolError

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext

_SQLITE_RECURSIVE = getattr(sqlite3, "SQLITE_RECURSIVE", 33)
_MAX_CELL_CHARS = 300

SQL_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "A single SQLite SELECT statement (WITH ... SELECT is allowed).",
        }
    },
    "required": ["query"],
}


def _strip_leading_comments(sql: str) -> str:
    sql = sql.strip()
    while True:
        if sql.startswith("--"):
            sql = sql.split("\n", 1)[1] if "\n" in sql else ""
        elif sql.startswith("/*") and "*/" in sql:
            sql = sql.split("*/", 1)[1]
        else:
            return sql.strip()


def run_sql_query(
    query: str, *, db_path: Path, allowed_tables: frozenset[str], row_limit: int = 50
) -> dict:
    head = _strip_leading_comments(query)
    if not re.match(r"^(SELECT|WITH)\b", head, re.IGNORECASE):
        raise ToolError("Only SELECT statements are allowed (optionally starting with WITH).")

    def authorizer(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return sqlite3.SQLITE_OK if arg1 in allowed_tables else sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_FUNCTION, _SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    try:
        # Path.as_uri() renders a proper file:/// URI (Windows drive letters,
        # spaces and backslashes included) — a raw f"file:{path}" breaks there.
        conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    except (sqlite3.OperationalError, ValueError) as exc:
        raise ToolError(f"Database not available: {exc}") from exc
    try:
        conn.row_factory = sqlite3.Row
        conn.set_authorizer(authorizer)
        try:
            cursor = conn.execute(head)
        except sqlite3.Warning as exc:  # multi-statement strings
            raise ToolError("Only a single SQL statement is allowed per call.") from exc
        except sqlite3.DatabaseError as exc:
            msg = str(exc)
            if "not authorized" in msg or "prohibited" in msg:
                raise ToolError(
                    "Query touches a table outside your allowlist or a non-SELECT "
                    f"operation. Tables you may read: {', '.join(sorted(allowed_tables))}."
                ) from exc
            if "one statement at a time" in msg:
                raise ToolError("Only a single SQL statement is allowed per call.") from exc
            raise ToolError(f"SQL error: {msg}") from exc
        columns = [d[0] for d in cursor.description] if cursor.description else []
        fetched = cursor.fetchmany(row_limit + 1)
        truncated = len(fetched) > row_limit
        rows = []
        for row in fetched[:row_limit]:
            rows.append([_fmt_cell(v) for v in row])
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }
    finally:
        conn.close()


def _fmt_cell(v):
    if isinstance(v, str) and len(v) > _MAX_CELL_CHARS:
        return v[:_MAX_CELL_CHARS] + "…"
    return v


def _render(result: dict) -> str:
    lines = [" | ".join(result["columns"])] if result["columns"] else []
    for row in result["rows"]:
        lines.append(" | ".join("NULL" if v is None else str(v) for v in row))
    body = "\n".join(lines) if lines else "(no rows)"
    suffix = f"\n({result['row_count']} rows"
    suffix += ", TRUNCATED — narrow your query or aggregate)" if result["truncated"] else ")"
    return body + suffix


def make_sql_query_tool(
    *, db_path: Path, allowed_tables: list[str], schema_doc: str, row_limit: int = 50
) -> Tool:
    allow = frozenset(allowed_tables)

    async def handler(tool_input: dict, ctx: "ToolContext") -> str:
        query = tool_input.get("query", "")
        if not query.strip():
            raise ToolError("Empty query.")
        result = run_sql_query(query, db_path=db_path, allowed_tables=allow, row_limit=row_limit)
        return _render(result)

    return Tool(
        name="sql_query",
        description=(
            "Run a read-only SQL SELECT against the company database (SQLite dialect). "
            f"Results are capped at {row_limit} rows — aggregate rather than dumping tables.\n\n"
            "Schema of the tables you can read:\n" + schema_doc
        ),
        input_schema=SQL_QUERY_SCHEMA,
        handler=handler,
    )
