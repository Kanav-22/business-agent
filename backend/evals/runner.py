"""Run deterministic evaluation cases through the real agent runtime.

The library path (`run_cases`) is intentionally separate from the CLI so tests,
scheduled comparisons, and future UI actions can share one execution contract.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from app.agents.budget import TokenBudget
from app.api.reports import get_report, save_report
from app.api.venture import save_eval_result
from app.config import Settings
from app.data.synthetic import SyntheticProvider
from app.db import make_engine
from evals.rubric import score_output

try:
    from app.venture.workflows import run_debate
except ImportError:  # V4 can still list cases when V3 has not been merged.
    run_debate = None


CASES_DIR = Path(__file__).resolve().parent / "cases"

AGENT_FOR_CASE = {
    "ceo": "venture_ceo",
    "cfo": "venture_cfo",
    "cmo": "venture_cmo",
    "cto": "venture_cto",
    "researcher": "researcher",
    "sales": "sales",
    "risk": "risk",
    "coo": "coo",
    "board": "__debate__",
}

_REQUIRED_FIELDS = {
    "id",
    "agent",
    "title",
    "scenario",
    "expected_elements",
    "bad_signs",
    "min_numbers",
    "pass_score",
    "improvement_suggestions",
}


async def _noop_event(event: dict) -> None:
    return None


def _case_error(path: Path, message: str) -> ValueError:
    return ValueError(f"{path.name}: {message}")


def _require_text(path: Path, value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _case_error(path, f"{field} must be a non-empty string")
    return value


def _validate_pattern_item(
    path: Path,
    item,
    index: int,
    *,
    collection: str,
    numeric_field: str,
    positive: bool,
) -> None:
    if not isinstance(item, dict):
        raise _case_error(path, f"{collection}[{index}] must be an object")
    _require_text(path, item.get("name"), f"{collection}[{index}].name")
    pattern = _require_text(
        path,
        item.get("pattern"),
        f"{collection}[{index}].pattern",
    )
    try:
        re.compile(pattern, re.IGNORECASE | re.DOTALL)
    except re.error as exc:
        raise _case_error(
            path,
            f"{collection}[{index}].pattern is invalid: {exc}",
        ) from exc
    number = item.get(numeric_field)
    if (
        isinstance(number, bool)
        or not isinstance(number, (int, float))
        or not math.isfinite(float(number))
    ):
        raise _case_error(
            path,
            f"{collection}[{index}].{numeric_field} must be a finite number",
        )
    if (positive and number <= 0) or (not positive and number < 0):
        qualifier = "greater than zero" if positive else "zero or greater"
        raise _case_error(
            path,
            f"{collection}[{index}].{numeric_field} must be {qualifier}",
        )


def load_case(path: Path) -> dict:
    """Load and validate one case, including regex compilation."""
    try:
        case = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _case_error(path, f"could not load valid JSON: {exc}") from exc
    if not isinstance(case, dict):
        raise _case_error(path, "case must be a JSON object")
    missing = sorted(_REQUIRED_FIELDS - set(case))
    if missing:
        raise _case_error(path, f"missing fields: {', '.join(missing)}")

    case_id = _require_text(path, case["id"], "id")
    if len(case_id) > 60:
        raise _case_error(path, "id must be at most 60 characters")
    agent = _require_text(path, case["agent"], "agent")
    if agent not in AGENT_FOR_CASE:
        raise _case_error(
            path,
            f"agent must be one of: {', '.join(AGENT_FOR_CASE)}",
        )
    _require_text(path, case["title"], "title")
    scenario = _require_text(path, case["scenario"], "scenario")
    if not scenario.lstrip().upper().startswith("TOPIC:"):
        raise _case_error(path, "scenario must start with a TOPIC: line")
    first_line = scenario.lstrip().splitlines()[0]
    if not first_line.split(":", 1)[1].strip():
        raise _case_error(path, "TOPIC: line must contain a topic")

    expected = case["expected_elements"]
    if not isinstance(expected, list) or not expected:
        raise _case_error(path, "expected_elements must be a non-empty array")
    for index, item in enumerate(expected):
        _validate_pattern_item(
            path,
            item,
            index,
            collection="expected_elements",
            numeric_field="weight",
            positive=True,
        )

    bad_signs = case["bad_signs"]
    if not isinstance(bad_signs, list):
        raise _case_error(path, "bad_signs must be an array")
    for index, item in enumerate(bad_signs):
        _validate_pattern_item(
            path,
            item,
            index,
            collection="bad_signs",
            numeric_field="penalty",
            positive=True,
        )

    min_numbers = case["min_numbers"]
    if isinstance(min_numbers, bool) or not isinstance(min_numbers, int) or min_numbers < 0:
        raise _case_error(path, "min_numbers must be an integer zero or greater")
    pass_score = case["pass_score"]
    if (
        isinstance(pass_score, bool)
        or not isinstance(pass_score, (int, float))
        or not 0 <= pass_score <= 10
    ):
        raise _case_error(path, "pass_score must be between 0 and 10")
    suggestions = case["improvement_suggestions"]
    if not isinstance(suggestions, list) or not suggestions:
        raise _case_error(path, "improvement_suggestions must be a non-empty array")
    for index, suggestion in enumerate(suggestions):
        _require_text(path, suggestion, f"improvement_suggestions[{index}]")
    return case


def load_cases(case_dir: Path = CASES_DIR) -> list[dict]:
    """Load every JSON case in stable filename order and reject duplicate IDs."""
    cases: list[dict] = []
    seen_ids: dict[str, str] = {}
    for path in sorted(case_dir.glob("*.json")):
        case = load_case(path)
        prior = seen_ids.get(case["id"])
        if prior:
            raise _case_error(path, f"duplicate id also used by {prior}")
        seen_ids[case["id"]] = path.name
        cases.append(case)
    return cases


def _topic_from_scenario(case: dict) -> str:
    for line in case["scenario"].splitlines():
        if line.strip().upper().startswith("TOPIC:"):
            return line.split(":", 1)[1].strip()
    return ""


def _resolve_agent(service, case_agent: str):
    runtime_name = AGENT_FOR_CASE[case_agent]
    if runtime_name == "researcher":
        return service.specialists[runtime_name]
    return service.venture_team[runtime_name]


async def run_cases(service, engine, cases: list[dict]) -> list[dict]:
    """Run, score, and persist cases sequentially with a fresh budget each."""
    collected: list[dict] = []
    for case in cases:
        if case["agent"] == "board" and run_debate is None:
            collected.append(
                {
                    "case_id": case["id"],
                    "agent": case["agent"],
                    "score": 0.0,
                    "passed": False,
                    "error": "skipped: debate workflow unavailable",
                    "skipped": True,
                }
            )
            continue

        output = ""
        error = None
        try:
            if case["agent"] == "board":
                report_id = await run_debate(
                    service,
                    engine,
                    topic=_topic_from_scenario(case),
                )
                report = get_report(engine, report_id)
                output = report["content"] if report else ""
                if report is None:
                    error = "debate report was not found after the workflow run"
            else:
                result = await _resolve_agent(service, case["agent"]).run(
                    case["scenario"],
                    on_event=_noop_event,
                    budget=TokenBudget(limit=service.settings.token_budget),
                )
                output = result.output or ""
                error = result.error
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        scored = score_output(case, output)
        save_eval_result(
            engine,
            case_id=case["id"],
            agent=case["agent"],
            model=service.settings.agent_model,
            score=scored["score"],
            passed=scored["passed"],
            details={
                "criteria": scored["criteria"],
                "suggestions": scored["suggestions"],
                "error": error,
            },
        )
        collected.append(
            {
                "case_id": case["id"],
                "agent": case["agent"],
                "score": scored["score"],
                "passed": scored["passed"],
                "error": error,
            }
        )
    return collected


def _averages(results: list[dict]) -> tuple[dict[str, float], float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for result in results:
        if not result.get("skipped"):
            grouped[result["agent"]].append(float(result["score"]))
    per_agent = {
        agent: round(sum(scores) / len(scores), 1)
        for agent, scores in sorted(grouped.items())
    }
    all_scores = [score for scores in grouped.values() for score in scores]
    overall = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
    return per_agent, overall


def render_scoreboard(results: list[dict]) -> str:
    """Render a fixed-width console scoreboard and aggregate averages."""
    lines = [
        f"{'CASE':<36} {'AGENT':<12} {'SCORE':>6}  RESULT",
        f"{'-' * 36} {'-' * 12} {'-' * 6}  {'-' * 6}",
    ]
    for result in results:
        if result.get("skipped"):
            score_text, status = "-", "SKIP"
        else:
            score_text = f"{float(result['score']):.1f}"
            status = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"{result['case_id'][:36]:<36} {result['agent']:<12} "
            f"{score_text:>6}  {status}"
        )
    per_agent, overall = _averages(results)
    lines.extend(["", "Per-agent averages:"])
    lines.extend(f"  {agent:<12} {score:>4.1f}" for agent, score in per_agent.items())
    lines.extend(["", f"Overall average: {overall:.1f}"])
    return "\n".join(lines)


def render_markdown_scoreboard(results: list[dict], model: str) -> str:
    """Render the persisted eval report from the same result rows."""
    lines = [
        f"# Evaluation run: {model}",
        "",
        "| Case | Agent | Score | Result | Error |",
        "|---|---|---:|---|---|",
    ]
    for result in results:
        status = (
            "SKIP"
            if result.get("skipped")
            else ("PASS" if result["passed"] else "FAIL")
        )
        score_text = "-" if result.get("skipped") else f"{result['score']:.1f}"
        error = (result.get("error") or "").replace("|", "/")
        lines.append(
            f"| {result['case_id']} | {result['agent']} | {score_text} | "
            f"{status} | {error} |"
        )
    per_agent, overall = _averages(results)
    lines.extend(["", "## Per-agent averages", ""])
    lines.extend(f"- {agent}: {score:.1f}" for agent, score in per_agent.items())
    lines.extend(["", f"**Overall average:** {overall:.1f}", ""])
    return "\n".join(lines)


def _select_cases(cases: list[dict], *, agent: str | None, case_id: str | None) -> list[dict]:
    selected = cases
    if agent:
        selected = [case for case in selected if case["agent"] == agent]
    if case_id:
        selected = [case for case in selected if case["id"] == case_id]
    return selected


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=sorted(AGENT_FOR_CASE), help="Run one role")
    parser.add_argument("--case", dest="case_id", help="Run one case ID")
    parser.add_argument("--list", action="store_true", help="List cases and exit")
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save the markdown scoreboard to the reports library",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    cases = _select_cases(
        load_cases(),
        agent=args.agent,
        case_id=args.case_id,
    )
    if not cases:
        print("No evaluation cases matched the selected filters.")
        return 0
    if args.list:
        print(f"{'CASE':<36} {'AGENT':<12} TITLE")
        for case in cases:
            print(f"{case['id'][:36]:<36} {case['agent']:<12} {case['title']}")
        return 0

    settings = Settings.from_env()
    engine = make_engine(settings.db_path)
    SyntheticProvider(seed=settings.data_seed).provision(engine)

    from app.agents.service import AgentService

    service = AgentService(settings)
    results = asyncio.run(run_cases(service, engine, cases))
    print(render_scoreboard(results))
    if args.save_report:
        report_id = save_report(
            engine,
            title=f"Eval run: {settings.agent_model}",
            content=render_markdown_scoreboard(results, settings.agent_model),
            agent="evals",
            kind="eval",
        )
        print(f"\nSaved eval report #{report_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
