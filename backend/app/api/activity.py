"""Agent Activity feed: run summaries assembled from the JSONL decision logs.

The logs are the source of truth for "who ran, why, what tools they called,
what it cost" — this module just aggregates them per run_id.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_MAX_LOG_FILES = 5  # newest N daily files
_TASK_PREVIEW = 240


def get_activity(
    logs_dir: Path,
    *,
    limit: int = 50,
    input_price_per_mtok: float = 3.0,
    output_price_per_mtok: float = 15.0,
) -> list[dict]:
    runs: dict[str, dict] = {}
    order: list[str] = []

    for path in sorted(logs_dir.glob("decisions-*.jsonl"))[-_MAX_LOG_FILES:]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            run_id = event.get("run_id")
            if not run_id:
                continue
            etype = event.get("type")
            if etype == "run_started":
                runs[run_id] = {
                    "run_id": run_id,
                    "parent_run_id": event.get("parent_run_id"),
                    "agent": event.get("agent"),
                    "agent_display": event.get("agent_display"),
                    "color": event.get("color"),
                    "depth": event.get("depth", 0),
                    "task": (event.get("task") or "")[:_TASK_PREVIEW],
                    "started_at": event.get("ts"),
                    "status": "running",
                    "tools": Counter(),
                    "duration_ms": None,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "error": None,
                }
                order.append(run_id)
            elif run_id in runs:
                run = runs[run_id]
                if etype == "tool_call":
                    run["tools"][event.get("tool") or "?"] += 1
                elif etype == "run_completed":
                    usage = event.get("usage") or {}
                    run["status"] = "error" if event.get("error") else "completed"
                    run["error"] = event.get("error")
                    run["duration_ms"] = event.get("duration_ms")
                    run["input_tokens"] = usage.get("input_tokens", 0)
                    run["output_tokens"] = usage.get("output_tokens", 0)

    results = []
    for run_id in reversed(order[-limit:]):
        run = runs[run_id]
        cost = (
            run["input_tokens"] / 1_000_000 * input_price_per_mtok
            + run["output_tokens"] / 1_000_000 * output_price_per_mtok
        )
        results.append(
            {
                **run,
                "tools": [
                    {"tool": name, "count": count}
                    for name, count in sorted(run["tools"].items())
                ],
                "cost_usd": round(cost, 4),
            }
        )
    return results
