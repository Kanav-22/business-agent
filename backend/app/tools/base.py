"""Shared tool registry.

A Tool is a name + description + JSON schema + async handler. Agents are
configured with a *subset* of tool names (least privilege); the registry
resolves names to schemas for the API call and dispatches execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.base import ToolContext

ToolHandler = Callable[[dict, "ToolContext"], Awaitable[str]]


class ToolError(Exception):
    """Raised by handlers for expected failures; message is shown to the agent."""


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: ToolHandler

    def to_api_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def schemas(self, names: list[str]) -> list[dict]:
        return [self._tools[n].to_api_schema() for n in names]

    def has(self, name: str) -> bool:
        return name in self._tools

    async def execute(self, name: str, tool_input: dict, ctx: "ToolContext") -> tuple[str, bool]:
        """Returns (result_text, is_error). Never raises for tool-level failures."""
        if name not in self._tools:
            return f"Unknown tool: {name}", True
        try:
            return await self._tools[name].handler(tool_input or {}, ctx), False
        except ToolError as exc:
            return f"Tool error: {exc}", True
        except Exception as exc:  # defensive: agent loop must survive tool bugs
            return f"Tool {name} failed unexpectedly: {type(exc).__name__}: {exc}", True
