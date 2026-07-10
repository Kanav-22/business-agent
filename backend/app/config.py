"""Application settings, read from environment variables with sensible defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    db_path: Path = BACKEND_ROOT / "data" / "lumina.db"
    logs_dir: Path = BACKEND_ROOT / "logs"
    agent_model: str = "claude-sonnet-4-6"
    agent_max_tokens: int = 4096
    # Whole-request token budget (input + output across every agent in the tree).
    token_budget: int = 150_000
    # CEO is depth 0; specialists are depth 1; sub-teams (Phase 3) will be depth 2.
    max_delegation_depth: int = 2
    max_agent_turns: int = 12
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    data_seed: int = 7
    # Prices used for the Activity page cost estimates (claude-sonnet-4-6).
    input_price_per_mtok: float = 3.0
    output_price_per_mtok: float = 15.0

    @classmethod
    def from_env(cls) -> "Settings":
        s = cls()
        if db := os.environ.get("BUSINESS_AGENT_DB"):
            s.db_path = Path(db)
        if logs := os.environ.get("BUSINESS_AGENT_LOGS"):
            s.logs_dir = Path(logs)
        s.agent_model = os.environ.get("AGENT_MODEL", s.agent_model)
        s.token_budget = int(os.environ.get("AGENT_TOKEN_BUDGET", s.token_budget))
        s.data_seed = int(os.environ.get("DATA_SEED", s.data_seed))
        s.input_price_per_mtok = float(
            os.environ.get("AGENT_PRICE_INPUT_MTOK", s.input_price_per_mtok)
        )
        s.output_price_per_mtok = float(
            os.environ.get("AGENT_PRICE_OUTPUT_MTOK", s.output_price_per_mtok)
        )
        if origins := os.environ.get("CORS_ORIGINS"):
            s.cors_origins = [o.strip() for o in origins.split(",") if o.strip()]
        return s
