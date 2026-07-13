# Task V11 — Evals dashboard + LLM-judge mode

**Branch:** `codex/v11-evals-dashboard` (from the integration tip AFTER V10
is merged).
**Read first:** `AGENTS.md`, `backend/evals/runner.py` + `rubric.py`,
`backend/app/api/venture.py` (`list_eval_results`, `save_eval_result`),
`frontend/app/(app)/venture/page.tsx` (patterns), `docs/FREE_LLM_SETUP.md`
(the model-comparison workflow this page serves).

## Goal

Make model quality visible: a dedicated Evals page that compares models per
agent role, and an optional LLM-judge that grades outputs *semantically*
alongside the structural rubric — so choosing a free model becomes a
5-minute read instead of a scoreboard printout.

## 1. Backend — `backend/evals/judge.py`

- `JUDGE_SYSTEM_PROMPT`: a strict grader ("You are an evaluation judge…"):
  given the case's scenario, expected elements (names only), bad signs
  (names only), and the candidate output, return ONLY JSON:
  `{"score": <0-10 number>, "reasons": ["…", …]}` — score strictly; a
  generic answer that merely mentions keywords deserves ≤4. The prompt must
  NOT contain any demo-marker phrase (check `simulated._MARKERS`).
- `async def judge_output(service, case, output) -> dict | None`: runs a
  bare model call through the service's client (reuse the pattern of
  `Agent.run`? NO — simpler: instantiate a one-off
  `Agent(AgentConfig(name="judge", …tools=[]…), empty registry, service's
  client factory…)` is heavyweight; instead call
  `service._get_client().messages.create(...)` directly with
  `model=service.settings.agent_model`, `max_tokens=500`, the judge system
  prompt, and one user message). Parse defensively: extract the first JSON
  object in the text; clamp score to [0,10], round 1 decimal; on any
  parse/API failure return `None` (never raise).
- DEMO_MODE: the simulated client has no judge playbook — `judge_output`
  must detect a non-JSON/canned reply and return `None` gracefully (the
  defensive parser already covers this; add an explicit test).

## 2. Runner integration

- `--judge` CLI flag and a `judge: bool = False` parameter on `run_cases`.
  When on and the run produced non-empty output: call `judge_output`; store
  under `details["judge"] = {"score": …, "reasons": […]}` (or
  `{"skipped": "<reason>"}` when None). **No schema change** — it rides in
  `details_json`. `passed` stays purely structural (the deterministic
  rubric remains the gate; the judge is advisory — state this in
  `evals/README.md`).
- Scoreboards (console + markdown) gain a `JUDGE` column showing the judge
  score or `-`.

## 3. API — `backend/app/main.py` (venture section) + `app/api/venture.py`

`GET /api/evals/summary` → deterministic aggregation of `eval_results`:

```json
{"models": [{"model": "...", "runs": N, "agents": {"cfo": {"avg": 6.2, "judge_avg": 5.8|null, "passed": 3, "total": 4}, ...}, "overall_avg": ..., "overall_judge_avg": ...|null}, ...]}
```

Implemented in `app/api/venture.py` (`eval_summary(engine)`), newest-first
model ordering by latest run.

## 4. Frontend — `frontend/app/(app)/evals/page.tsx` + wiring

- Sidebar entry `{ href: "/evals", label: "Evals", icon: Gauge }` +
  metadata layout file, following the existing `(app)` conventions.
- Sections: (1) **Model comparison matrix** — models as columns, agent
  roles as rows, cell = avg score (structural, with judge avg beneath when
  present), color-scaled (red <5, amber 5-7, green ≥7); (2) **Run history**
  — table from `/api/evals` with model/agent/case filters, expandable rows
  showing criteria breakdown, judge reasons, and improvement suggestions;
  (3) empty state with the copy-pasteable runner commands from
  `docs/FREE_LLM_SETUP.md`.
- Remove the small evals table from the Venture Studio page ONLY if it
  exists there; replace with a link to `/evals` (allowed exception to
  append-only, keep the diff minimal).
- `types.ts`: `EvalSummary` interfaces (append).

## 5. Tests — `backend/tests/test_evals_judge.py`

1. Judge parser: valid JSON in prose → parsed+clamped; garbage / canned
   demo text → `None`; score 15 → clamped 10.
2. `run_cases(judge=True)` with a FakeClient scripting BOTH the agent
   output and a judge reply (dict mode keyed on the judge system prompt's
   unique substring): `details["judge"]["score"]` persisted; `passed`
   unchanged by judge.
3. `eval_summary`: seed 3-4 eval rows across two models → exact averages,
   judge_avg null when absent.
4. Existing suite untouched-green.

## Constraints

`AGENTS.md` hard rules; no new dependencies; judge is advisory only
(structural `passed` untouched); no demo-marker collisions in the judge
prompt; frontend `npm run build` green.

## Acceptance checklist

- [ ] Full pytest green; build green; CI (from V10) green on the branch.
- [ ] Demo smoke: `DEMO_MODE=1 python3 -m evals.runner --judge` completes
      with judge columns showing `-` (skipped), rows persisted; `/evals`
      page renders the matrix from those rows.
