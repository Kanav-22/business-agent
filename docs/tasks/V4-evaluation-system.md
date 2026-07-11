# Task V4 — Agent Evaluation System

**Branch:** `codex/v4-evals` (from the integration branch AFTER V3 is merged;
if V3 isn't merged yet, branch from latest integration and skip the `board`
case's workflow run — see below).
**Read first:** `AGENTS.md`, `docs/survival/*.md` (the quality bars the rubric
encodes), `backend/app/api/venture.py` (`save_eval_result`),
`backend/tests/fake_anthropic.py`.

## Goal

A zero-dependency eval harness that runs scenario cases through the real
agents, scores outputs with a deterministic structural rubric (0–10), persists
`EvalResult` rows, and prints a scoreboard — so a weaker/cheaper model can be
compared against the current one (`AGENT_MODEL` env + optional
`SURVIVAL_MODE=1`).

## 1. Package layout

```
backend/evals/__init__.py          # empty
backend/evals/rubric.py            # deterministic scorer
backend/evals/runner.py            # CLI + run_cases() library function
backend/evals/cases/<agent>_<n>.json
backend/evals/README.md
```

## 2. Case JSON schema (validate on load; raise ValueError with filename)

```json
{
  "id": "ceo_bootstrap_founder",
  "agent": "ceo",
  "title": "Bootstrap founder, ₹50k / 30 days",
  "scenario": "TOPIC: ...\n<the full task text sent to the agent>",
  "expected_elements": [
    {"name": "clear niche", "pattern": "niche|segment|dermatolog", "weight": 2},
    {"name": "pricing with numbers", "pattern": "₹|\\$|price", "weight": 2}
  ],
  "bad_signs": [
    {"name": "generic advice", "pattern": "work hard|stay focused|be consistent", "penalty": 1.5}
  ],
  "min_numbers": 3,
  "pass_score": 6.0,
  "improvement_suggestions": [
    "Add concrete numbers (budget split, price, targets).",
    "Name a niche narrow enough to list 100 prospects."
  ]
}
```

`agent` ∈ `{ceo, cfo, cmo, cto, researcher, sales, risk, coo, board}` mapping
to runtime agents:

```python
AGENT_FOR_CASE = {
    "ceo": "venture_ceo", "cfo": "venture_cfo", "cmo": "venture_cmo",
    "cto": "venture_cto", "researcher": "researcher", "sales": "sales",
    "risk": "risk", "coo": "coo", "board": "__debate__",
}
```

`board` cases run `run_debate(service, engine, topic=<scenario's TOPIC line>)`
and score the saved report content. If `app.venture.workflows` is not
importable (V3 unmerged), `--list` still works and board cases are reported as
`skipped` — do not crash.

## 3. `rubric.py`

```python
GENERIC_BAD_SIGNS = [  # applied to EVERY case in addition to its own
  {"name": "hype cliché", "pattern": r"game-?chang|revolutioniz|cutting[- ]edge|unlock (growth|potential)|synerg", "penalty": 1.0},
  {"name": "hedging non-answer", "pattern": r"it depends|there are many factors|only time will tell", "penalty": 1.0},
]

def score_output(case: dict, output: str) -> dict:
    """Returns {"score": float 0-10 (1 decimal), "passed": bool,
    "criteria": [{"name", "kind": "expected|bad_sign|numbers", "hit": bool,
                  "weight_or_penalty": float}],
    "suggestions": [str]  # the case's improvement_suggestions, only when failed
    }"""
```

Algorithm (deterministic, documented in the module docstring):
1. `base = 10 * matched_weight / total_weight` over `expected_elements`
   (regex, `re.IGNORECASE | re.DOTALL`, search not match).
2. Subtract `penalty` for each matched bad sign (case's + generic).
3. Numbers check: count regex `\d[\d,.]*%?|₹|\$` matches; if
   `< min_numbers`, subtract `1.5` and record a `numbers` criterion.
4. Clamp to [0, 10], round to 1 decimal. `passed = score >= pass_score`.
5. Empty/whitespace output → score 0, all criteria missed.

## 4. `runner.py`

Library function first (this is what tests use):

```python
async def run_cases(service, engine, cases: list[dict]) -> list[dict]:
    # for each case: resolve agent, run with a fresh
    # TokenBudget(limit=service.settings.token_budget) and a noop on_event,
    # score_output(case, result.output or ""), persist via
    # save_eval_result(engine, case_id=..., agent=case["agent"],
    #                  model=service.settings.agent_model, score=..., passed=...,
    #                  details={"criteria": ..., "suggestions": ..., "error": result.error}),
    # collect {"case_id", "agent", "score", "passed", "error"}.
```

CLI (`python -m evals.runner`, argparse):
`--agent X` filter, `--case ID` filter, `--list` (print cases, exit),
`--save-report` (after the run, `save_report(engine, title="Eval run: <model>",
content=<markdown scoreboard>, agent="evals", kind="eval")`). Settings from
`Settings.from_env()` (DEMO_MODE honored), engine `make_engine(settings.db_path)`,
`AgentService(settings)`. Print a fixed-width scoreboard (case, agent, score,
PASS/FAIL) + per-agent averages + overall average. Exit code 0 regardless of
pass/fail (it's a report, not a gate).

## 5. Cases — ≥2 per role, 9 roles (≥18 files)

Content quality matters more than quantity; write scenarios a real founder
would ask, with expected elements that mirror the "Required output structure"
of each agent's survival guide (`docs/survival/`). Required among them:

- `ceo_bootstrap_founder.json` — the spec's example: founder with ₹50,000,
  30 days, basic coding, wants an AI automation business. Expected: niche,
  offer, MVP, acquisition plan, pricing, risks, 7-day/first-steps plan.
  Bad signs: generic advice, no numbers, "raise funding".
- One `risk` case where the scenario hides a compliance landmine (e.g. storing
  patient data) — expected elements include ranking and jurisdiction; a `risk`
  case must fail if the output lacks a verdict.
- One `board` case (debate output structure: all 9 sections).
- One `sales` case checking word-count discipline is NOT scoreable by regex —
  instead expect subject line, single CTA, risk-reversal, A/B variant.

Every case file must load, validate, and be exercised by the round-trip test
below (parametrized over all case files: rubric on the case's OWN
`improvement_suggestions` text should score LOW — a cheap sanity check that
patterns aren't trivially matched).

## 6. `README.md` (evals)

How to run (demo / live / weaker model / survival mode), how scores work, how
to add a case, and the model-comparison workflow:

```bash
DEMO_MODE=1 python3 -m evals.runner --save-report          # $0 smoke
AGENT_MODEL=claude-sonnet-4-6 python3 -m evals.runner      # baseline
AGENT_MODEL=<weaker> python3 -m evals.runner               # candidate
AGENT_MODEL=<weaker> SURVIVAL_MODE=1 python3 -m evals.runner  # candidate + kit
# compare per-agent averages across the three runs (/api/evals or the printed table)
```

## 7. Tests — `backend/tests/test_evals.py`

1. Rubric: a handcrafted GOOD answer for the ceo case (contains niche, offer,
   numbers, steps…) scores ≥ pass_score; a handcrafted BAD answer ("Do market
   research, stay focused, and execute consistently. It depends on many
   factors.") scores < 4 and triggers the generic bad signs; empty output → 0.
2. All case files load + validate; parametrized sanity check per §5.
3. `run_cases` smoke with a demo-mode service (`Settings(demo_mode=True)`,
   `AgentService(settings)` — no key needed) on 2 non-board cases: rows appear
   via `list_eval_results`, scores within [0, 10], `model` recorded. Do NOT
   assert `passed=True` (demo output is canned).
4. `GET /api/evals` returns the persisted rows (TestClient, existing pattern).

## Acceptance checklist

- [ ] `python3 -m pytest` green.
- [ ] `DEMO_MODE=1 python3 -m evals.runner --save-report` prints a scoreboard,
      persists rows, saves a `kind="eval"` report.
- [ ] No changes outside `backend/evals/**`, `backend/tests/test_evals.py`.
      (`/api/evals` endpoint already exists.)
