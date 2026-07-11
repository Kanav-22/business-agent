"""save_memory — validated write path into the long-term memory store.

Like create_task/report_writer: the agent proposes, deterministic code
validates (category allowlist per agent — least privilege — plus size caps)
and performs the insert. Category semantics: docs/MEMORY_SYSTEM.md."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.engine import Engine

from app.api.venture import MAX_MEMORY_CONTENT, MEMORY_CATEGORIES, save_memory_record
from app.tools.base import Tool, ToolError

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext


def make_save_memory_tool(engine: Engine, allowed_categories: list[str]) -> Tool:
    invalid = sorted(set(allowed_categories) - set(MEMORY_CATEGORIES))
    if invalid:  # configuration bug, fail at construction not at runtime
        raise ValueError(f"unknown memory categories in allowlist: {invalid}")

    async def handler(tool_input: dict, ctx: "ToolContext") -> str:
        category = (tool_input.get("category") or "").strip()
        title = (tool_input.get("title") or "").strip()
        content = (tool_input.get("content") or "").strip()
        related_idea = (tool_input.get("related_idea") or "").strip() or None

        if category not in MEMORY_CATEGORIES:
            raise ToolError(
                f"invalid category {category!r}; valid: {', '.join(MEMORY_CATEGORIES)}."
            )
        if category not in allowed_categories:
            raise ToolError(
                f"this agent may only save categories: {', '.join(allowed_categories)}."
            )
        if not title:
            raise ToolError("title is required.")
        if len(title) > 200:
            raise ToolError("title must be at most 200 characters.")
        if not content:
            raise ToolError("content is required.")
        if len(content) > MAX_MEMORY_CONTENT:
            raise ToolError(f"content exceeds {MAX_MEMORY_CONTENT} characters.")

        memory_id = save_memory_record(
            engine,
            category=category,
            title=title,
            content=content,
            source_agent=ctx.agent,
            related_idea=related_idea,
        )
        return f"Saved memory #{memory_id} [{category}]: {title!r}."

    return Tool(
        name="save_memory",
        description=(
            "Save a short, retrievable memory record (a decision, assumption, "
            "lesson or research finding) to the long-term memory store. Write it "
            "so a future agent can act on it without extra context. Allowed "
            f"categories for you: {', '.join(allowed_categories)}."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": allowed_categories,
                    "description": "Memory category.",
                },
                "title": {"type": "string", "description": "One-line summary (max 200 chars)."},
                "content": {
                    "type": "string",
                    "description": f"The record itself (max {MAX_MEMORY_CONTENT} chars).",
                },
                "related_idea": {
                    "type": "string",
                    "description": "Optional idea/business slug this relates to.",
                },
            },
            "required": ["category", "title", "content"],
        },
        handler=handler,
    )
