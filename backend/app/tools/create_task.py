"""create_task — the Workflow Coordinator's ONLY write path.

Per the spec's ground rules, agents never write to the database directly:
this handler validates every field deterministically, then executes the
insert itself. Anything invalid is rejected with an explanatory ToolError.
"""
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Employee, Task
from app.tools.base import Tool, ToolError

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext

DEPARTMENTS = [
    "Leadership",
    "Engineering",
    "Product",
    "Marketing",
    "Customer Success",
    "Operations",
]
STATUSES = ["open", "in_progress", "blocked"]

CREATE_TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short imperative task title (max 200 chars)."},
        "department": {"type": "string", "enum": DEPARTMENTS},
        "status": {
            "type": "string",
            "enum": STATUSES,
            "description": "Defaults to 'open'. Use 'blocked' only with blocked_reason.",
        },
        "assignee_name": {
            "type": "string",
            "description": "Optional employee full name (must match an existing employee).",
        },
        "due_date": {"type": "string", "description": "Optional ISO date YYYY-MM-DD."},
        "blocked_reason": {
            "type": "string",
            "description": "Required when status is 'blocked'; forbidden otherwise.",
        },
    },
    "required": ["title", "department"],
}


def validate_and_create_task(engine: Engine, tool_input: dict) -> dict:
    title = (tool_input.get("title") or "").strip()
    if not title:
        raise ToolError("title is required.")
    if len(title) > 200:
        raise ToolError("title must be at most 200 characters.")

    department = (tool_input.get("department") or "").strip()
    if department not in DEPARTMENTS:
        raise ToolError(f"department must be one of: {', '.join(DEPARTMENTS)}.")

    status = (tool_input.get("status") or "open").strip()
    if status not in STATUSES:
        raise ToolError(
            f"status must be one of: {', '.join(STATUSES)} (new tasks cannot be 'done')."
        )

    blocked_reason = (tool_input.get("blocked_reason") or "").strip() or None
    if status == "blocked" and not blocked_reason:
        raise ToolError("blocked_reason is required when status is 'blocked'.")
    if status != "blocked" and blocked_reason:
        raise ToolError("blocked_reason is only allowed when status is 'blocked'.")

    due_date = None
    if raw := (tool_input.get("due_date") or "").strip():
        try:
            due_date = dt.date.fromisoformat(raw)
        except ValueError as exc:
            raise ToolError(f"due_date must be ISO YYYY-MM-DD, got {raw!r}.") from exc

    with Session(engine) as session:
        assignee_id = None
        if name := (tool_input.get("assignee_name") or "").strip():
            employee = session.scalar(
                select(Employee).where(func.lower(Employee.name) == name.lower())
            )
            if employee is None:
                known = [e.name for e in session.scalars(select(Employee)).all()]
                raise ToolError(
                    f"No employee named {name!r}. Known employees: {', '.join(known)}."
                )
            assignee_id = employee.id

        task = Task(
            title=title,
            department=department,
            status=status,
            assignee_id=assignee_id,
            due_date=due_date,
            blocked_reason=blocked_reason,
            created_at=dt.date.today(),
        )
        session.add(task)
        session.commit()
        return {
            "id": task.id,
            "title": task.title,
            "department": task.department,
            "status": task.status,
            "assignee_id": assignee_id,
            "due_date": due_date.isoformat() if due_date else None,
        }


def make_create_task_tool(engine: Engine) -> Tool:
    async def handler(tool_input: dict, ctx: "ToolContext") -> str:
        created = validate_and_create_task(engine, tool_input)
        return (
            f"Created task #{created['id']}: {created['title']} "
            f"[{created['department']} / {created['status']}]"
            + (f", due {created['due_date']}" if created["due_date"] else "")
        )

    return Tool(
        name="create_task",
        description=(
            "Create a new task in the company task list. Input is validated by "
            "deterministic code before anything is written — invalid departments, "
            "statuses, dates or assignees are rejected. New tasks cannot be 'done'."
        ),
        input_schema=CREATE_TASK_SCHEMA,
        handler=handler,
    )
