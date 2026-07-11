# Review — Task V3 (`codex/v3-workflows` @ `0fb4bb2`)

Reviewer: Claude (architect). Scope, diff, tests, and runtime behavior
verified on a test merge against integration tip `ad9fd5d`.

## Verification performed

- Scope: exactly the three in-scope files, 992 insertions, zero deletions.
- Full suite on the merged tree: **97/97 passed** (85 pre-existing + 12 new).
- DEMO_MODE end-to-end (founder profile set): all four workflows produced
  reports with the required structure; idea row persisted with a
  deterministic TEST FIRST 5.5/10 verdict; memory rows landed in
  decision/risk/customer_research/business_idea; debate report contains all
  required headings and the founder context did not leak into report bodies;
  interviews report opens with the synthetic-data disclaimer.
- Event-contract check: the `score_idea` attribution wrapper matches
  `base.py`'s actual `tool_result` event shape (`tool`, `output`,
  `is_error`), and the parsed `Idea #N` marker sits before the event
  preview truncation point.

## Findings

BLOCKING: none.

IMPORTANT: none.

OPTIONAL:
1. `_run`'s pre-lookup display-name fallback (`"venture_ceo"` → `"Ceo"`) is
   cosmetically off for missing venture agents; only reachable in the
   missing-agent edge case, and the shipped test pins the current behavior.
   Fine to leave.
2. `WorkflowBody.topic` missing (vs. empty) returns FastAPI's 422 rather
   than 400 — acceptable convention; noting for the API docs in V5.

ARCHITECTURAL VERDICT: Conforms. Deterministic orchestration over
prompt-driven agents, single write paths respected, one budget per workflow,
error containment (`[X unavailable: …]`) exactly as specified. Two
ambiguity decisions taken by the implementer are improvements: (a) idea
attribution via the workflow's own tool-result event instead of
newest-row, eliminating a cross-run race my spec would have allowed; (b)
strong references held for background tasks, which the pre-existing
`run_job` endpoint doesn't do.

TESTING VERDICT: Exceeds spec. 12 tests including true-concurrency barrier
tests for both parallel fan-outs, budget-identity assertions, attribution
race tests, lock-release polling on the 409 path, and brief-content
contract checks (`TOPIC:` line, "Revise"/"objections" trigger words).

ACCEPT / REQUEST CHANGES: **ACCEPT** — merged into
`claude/agent-operating-system-66e55h`.
