"""Pluggable data layer.

Agents only ever see the database schema — they never know which provider
filled it. Phase 1 ships SyntheticProvider; Phase 5 adds RealBusinessProvider
(CSV import, Stripe, accounting exports) implementing this same interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Meta


class DataProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def provision(self, engine: Engine, *, force: bool = False) -> dict:
        """Fill the database. Returns a summary dict (row counts etc.).

        Must be idempotent: if data is already present and force=False, do nothing.
        """

    @staticmethod
    def is_provisioned(engine: Engine) -> bool:
        from app.models import Base

        Base.metadata.create_all(engine)
        with Session(engine) as session:
            return session.scalar(select(Meta).where(Meta.key == "generated_at")) is not None
