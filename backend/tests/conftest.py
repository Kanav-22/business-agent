from __future__ import annotations

import datetime as dt

import pytest

from app.config import Settings
from app.data.synthetic import SyntheticProvider
from app.db import make_engine

# Fixed anchor so tests are deterministic regardless of the wall clock:
# data window = 2025-01 .. 2026-06.
ANCHOR = dt.date(2026, 7, 1)
SEED = 42


@pytest.fixture(scope="session")
def seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test.db"
    engine = make_engine(db_path)
    SyntheticProvider(seed=SEED, anchor=ANCHOR).provision(engine, force=True)
    return db_path, engine


@pytest.fixture()
def settings(seeded_db, tmp_path) -> Settings:
    db_path, _ = seeded_db
    s = Settings()
    s.db_path = db_path
    s.logs_dir = tmp_path / "logs"
    s.scheduler_enabled = False  # tests trigger jobs directly
    return s
