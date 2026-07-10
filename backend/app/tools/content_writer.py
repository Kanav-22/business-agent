"""content_writer — the Content agent's ONLY output path.

Drafts are never published by the agent: deterministic validation runs first,
then the draft is inserted into the approvals inbox as 'pending'. A human
approves or rejects it in the dashboard.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.engine import Engine

from app.api.approvals import create_approval
from app.tools.base import Tool, ToolError

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext

CHANNELS = ["blog", "email", "social", "announcement"]
MIN_BODY = 50
MAX_BODY = 20_000

CONTENT_WRITER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Working title / subject line (max 200 chars)."},
        "channel": {
            "type": "string",
            "enum": CHANNELS,
            "description": "Where this would be published once approved.",
        },
        "body": {
            "type": "string",
            "description": "The full draft, markdown allowed. 50–20000 characters.",
        },
    },
    "required": ["title", "channel", "body"],
}


def validate_content_input(tool_input: dict) -> tuple[str, str, str]:
    title = (tool_input.get("title") or "").strip()
    if not title:
        raise ToolError("title is required.")
    if len(title) > 200:
        raise ToolError("title must be at most 200 characters.")
    channel = (tool_input.get("channel") or "").strip()
    if channel not in CHANNELS:
        raise ToolError(f"channel must be one of: {', '.join(CHANNELS)}.")
    body = (tool_input.get("body") or "").strip()
    if len(body) < MIN_BODY:
        raise ToolError(f"body must be at least {MIN_BODY} characters — write the full draft.")
    if len(body) > MAX_BODY:
        raise ToolError(f"body must be at most {MAX_BODY} characters.")
    return title, channel, body


def make_content_writer_tool(engine: Engine) -> Tool:
    async def handler(tool_input: dict, ctx: "ToolContext") -> str:
        title, channel, body = validate_content_input(tool_input)
        approval_id = create_approval(
            engine, kind="content", title=title, channel=channel, agent=ctx.agent, content=body
        )
        return (
            f"Draft #{approval_id} ({channel}) submitted to the Approvals inbox as "
            f"{title!r}. Nothing is published until a human approves it there."
        )

    return Tool(
        name="content_writer",
        description=(
            "Submit a finished content draft (blog post, email, social post, "
            "announcement) to the human Approvals inbox. This does NOT publish "
            "anything — a human reviews and approves/rejects in the dashboard. "
            "Write the complete draft in `body` (markdown allowed)."
        ),
        input_schema=CONTENT_WRITER_SCHEMA,
        handler=handler,
    )
