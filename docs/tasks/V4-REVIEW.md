# Review — Task V4 (`codex/v4-evals` @ `6313bd9`)

Reviewer: Claude (architect). Verified on a test merge against integration
tip `1865b2d` (combined with V5 for the final run).

## Verification performed

- Scope: exactly `backend/evals/**` (18 case files — 2 per role across all 9
  roles — rubric, runner, README, `__init__`) + `backend/tests/test_evals.py`.
  2,003 insertions, zero deletions.
- Full suite on the merged tree: **128/128 passed** (97 + 31 new incl. the
  per-case parametrized sanity checks).
- `DEMO_MODE=1 python3 -m evals.runner --save-report` end-to-end: 18 cases
  ran through the real agent runtime, scoreboard rendered, `eval_results`
  rows persisted, `kind="eval"` report saved. Demo-mode scores are coherent
  (researcher 0.0 — no web in demo; board 10.0 — the debate workflow's
  structure matches its rubric; canned venture answers land mid-range).

## Findings

BLOCKING: none.

IMPORTANT: none.

OPTIONAL:
1. `run_cases` executes sequentially; a `--parallel` flag would speed live
   model comparisons. Fine for now — live runs are budget-bound anyway.
2. Demo-mode CEO cases score low (3.5 avg) because canned proposals can't
   match case-specific expectations — worth a README sentence some day, but
   the runner's purpose is comparing *live* models, where this is moot.

ARCHITECTURAL VERDICT: Conforms. Library/CLI separation as specified;
case validation is stronger than spec (regex compilation at load, non-finite
number rejection, duplicate-ID detection, filename-attributed errors, UTF-8
failure handling); graceful degradation when the debate workflow is absent.

TESTING VERDICT: Exceeds spec. The parametrized
suggestions-don't-trivially-pass check runs against every case file; bad-sign
lookbehind behavior (rebuttals like "do not raise funding" not penalized) is
pinned by a dedicated test; corpus shape (≥2 cases per role, unique IDs) is
enforced by test, so future case additions cannot silently break coverage.

Case content quality (the judgment call this task hinged on): genuinely
good. Scenarios embed concrete traps (the patient-data case hides four
distinct compliance landmines; the CEO bootstrap case penalizes fundraising
advice with a lookbehind that spares explicit rebuttals). These are eval
cases a founder would actually learn from.

ACCEPT / REQUEST CHANGES: **ACCEPT** — merged into
`claude/agent-operating-system-66e55h`.
