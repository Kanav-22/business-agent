"""Append-only JSONL log of every agent decision: inputs, model output,
tool calls, tool results, usage. One line per event, one file per day."""
from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path


class DecisionLogger:
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self._lock = threading.Lock()

    def log(self, record: dict) -> None:
        record = {"logged_at": dt.datetime.now(dt.timezone.utc).isoformat(), **record}
        path = self.logs_dir / f"decisions-{dt.date.today():%Y%m%d}.jsonl"
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
