"""Per-request token budget shared by every agent in a delegation tree."""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    pass


@dataclass
class TokenBudget:
    limit: int
    input_tokens: int = 0
    output_tokens: int = 0
    by_agent: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def add(self, agent: str, usage) -> None:
        """usage: anthropic Usage object (or anything with the same attrs)."""
        inp = getattr(usage, "input_tokens", 0) or 0
        inp += getattr(usage, "cache_creation_input_tokens", 0) or 0
        inp += getattr(usage, "cache_read_input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        self.input_tokens += inp
        self.output_tokens += out
        per = self.by_agent.setdefault(agent, {"input_tokens": 0, "output_tokens": 0})
        per["input_tokens"] += inp
        per["output_tokens"] += out
        if self.total > self.limit:
            raise BudgetExceeded(
                f"Token budget exhausted: {self.total} > {self.limit} for this request."
            )

    def check_remaining(self) -> None:
        """Refuse to start another model call once the budget is spent."""
        if self.total > self.limit:
            raise BudgetExceeded(
                f"Token budget exhausted: {self.total} > {self.limit} for this request."
            )

    def snapshot(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total": self.total,
            "limit": self.limit,
            "by_agent": self.by_agent,
        }
