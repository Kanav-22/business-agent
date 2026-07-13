# Task V12 — Monday Founder Briefing (the weekly operating ritual)

**Branch:** `codex/v12-founder-briefing` (from the integration tip AFTER V11
is merged).
**Read first:** `AGENTS.md`, `backend/app/scheduler.py` (job pattern +
`JOBS`), `backend/app/venture/workflows.py` (`_run`, `_brief`),
`backend/app/api/kpis.py`, `backend/app/api/venture.py` (`list_memories`,
`list_ideas`), `backend/app/api/reports.py`.

## Goal

One report every Monday that a founder actually reads: company KPIs, what
the control check flagged, open risks, decisions awaiting their reversal
triggers, the idea pipeline, and pending approvals — digest assembled by
CODE, narrative written by the venture CEO. It lands as `kind='briefing'`,
so the Overview page surfaces it automatically with **zero frontend
changes**.

## 1. Digest assembly (deterministic) — in `backend/app/scheduler.py`

`def build_founder_digest(engine) -> str` returning markdown sections
(each capped/safe when empty):

1. **KPIs** — from `get_kpis(engine)`: MRR, active customers, cash, runway,
   open tasks (one line each, formatted like the Overview).
2. **Latest control check** — newest `kind='control_check'` report: first
   600 chars + report ref; "No control check yet." when absent.
3. **Open risks** — up to 5 newest active `risk` memories (title + first
   140 chars).
4. **Decisions on the clock** — up to 5 newest `decision` memories; flag
   lines containing "reverse if" verbatim.
5. **Idea pipeline** — up to 5 newest ideas: title, total, verdict label.
6. **Pending approvals** — count of `status='pending'` approvals
   (via `list_approvals`).
7. **Business identity line** — `service.company_context` is passed in by
   the caller, not queried here (keep the digest engine-only).

## 2. The job — `run_founder_briefing(service, engine) -> int`

Pattern of the existing jobs: build the digest, then run **`venture_ceo`**
(direct `.run()`, fresh `TokenBudget`, `_noop_event`) with a brief that
starts `TOPIC: Monday founder briefing for {service.company_context}` and
instructs: "Write the weekly founder briefing from the DIGEST below. Keep
it under ~400 words. Structure: What matters this week / Numbers /
Risks & decisions needing attention / One recommended focus. Do not invent
data — every number comes from the digest.\n\nDIGEST:\n{digest}".

Save via `save_report(engine, title=f"Founder briefing — {date}",
content=<agent output + '\n\n---\n\n## Digest (source data)\n' + digest>,
agent="venture_ceo", kind="briefing")`. Appending the raw digest keeps the
report trustworthy even if the model hallucinates (readers can check).

Register: `JOBS["founder_briefing"] = run_founder_briefing` and a cron
entry Mondays 06:50 in `create_scheduler` (after the existing 06:00/06:20/
06:40 jobs). The existing `weekly_briefing` job stays untouched — the CEO
ops briefing and the founder briefing are different documents.

DEMO_MODE: `venture_ceo`'s canned handler emits a proposal-shaped text —
acceptable; the appended digest section carries the real data. Note this in
the module docstring; do NOT add demo handlers.

## 3. Tests — `backend/tests/test_founder_briefing.py`

1. `build_founder_digest` on a writable seeded DB with: 1 risk memory,
   1 decision memory containing "reverse if", 1 scored idea, 1 pending
   approval, 1 control-check report → each section present with the right
   content; then on a bare DB → graceful empty-state lines, no exceptions.
2. `run_founder_briefing` with FakeClient (key: "venture strategist") →
   report saved with `kind='briefing'`, title prefix, agent output AND the
   `## Digest (source data)` section; the task sent to the agent contains
   the TOPIC line and the digest.
3. `JOBS` contains `founder_briefing`; `POST /api/jobs/founder_briefing/run`
   returns 202 (existing endpoint, TestClient).
4. Existing suite untouched-green (especially the Overview `/api/briefing`
   endpoint tests — the newest `kind='briefing'` may now be a founder
   briefing; check nothing asserts the old title format).

## Constraints

`AGENTS.md` hard rules; no frontend changes; no new deps; digest is code
(no agent queries inside `build_founder_digest`); the existing three cron
jobs and their times are untouched.

## Acceptance checklist

- [ ] Full pytest green; CI green on the branch.
- [ ] DEMO_MODE manual: `POST /api/jobs/founder_briefing/run` → briefing
      appears on the Overview page (latest briefing card) with real digest
      numbers beneath the narrative.
