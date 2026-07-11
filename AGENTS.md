# AGENTS.md — rules for AI implementers working on this repo

This repo is an **AI Business OS**: a FastAPI + Next.js multi-agent system with
two layers — an *operations layer* (CEO→C-suite agents answering questions
about the running company from SQLite) and a *venture layer* (founder-facing
agents/workflows for validating new businesses). Architecture roles: Claude
(architect/reviewer) designs and reviews; implementer agents (e.g. Codex)
execute the specs in `docs/tasks/`. Every implementer must follow this file.

## Hard rules (non-negotiable)

1. **Never break the operations layer.** Do not modify existing prompts, tools,
   endpoints, tables, or behavior. Existing files may only gain *additive*
   wiring (a new dict entry, a new endpoint block, an appended type).
2. **Stay inside your spec.** Implement exactly the task file you were given
   (`docs/tasks/*.md`). Do not refactor unrelated code, do not edit
   `AGENTS.md`, the specs, or `docs/` design documents.
3. **Tests must be green before every push**: `cd backend && python3 -m pytest`
   (85 tests pass as of V2). For frontend work, `cd frontend && npm run build`
   must also pass. Never delete or weaken an existing test; extending an
   assertion additively (superset) is allowed only when the spec says so.
4. **Agents never write to the DB directly.** All writes go through validated
   tool/factory functions (`app/tools/*.py` pattern: `make_X_tool(engine)`,
   deterministic validation raising `ToolError`, then a single write path in
   `app/api/*.py`).
5. **No new dependencies** without a written justification in the commit
   message; prefer the standard library.
6. **Branch protocol**: branch from the latest
   `claude/agent-operating-system-66e55h`, name it `codex/<phase>` (e.g.
   `codex/v3-workflows`), push there, and stop. The architect reviews and
   merges into the integration branch. Never push to the integration branch
   or `main` directly.
7. **Model identifiers, session URLs and marketing names do not belong in
   code, comments or commits.**

## Architecture map (read before coding)

| Area | File(s) |
|------|---------|
| Agent core (config + tool loop) | `backend/app/agents/base.py` |
| Roster wiring (operations + venture) | `backend/app/agents/service.py` |
| Venture prompts | `backend/app/venture/agents.py` |
| Demo mode (zero-cost simulated model) | `backend/app/agents/simulated.py` |
| Survival-mode prompt injection | `backend/app/agents/survival.py` + `docs/survival/` |
| Deterministic scoring / routing | `backend/app/venture/scoring.py`, `backend/app/venture/router.py` |
| Founder profile / memories / ideas persistence | `backend/app/venture/founder.py`, `backend/app/api/venture.py` |
| Validated write tools | `backend/app/tools/{create_task,report_writer,content_writer,save_memory,score_idea}.py` |
| Reports persistence | `backend/app/api/reports.py` (`save_report` is THE write path) |
| Scheduled jobs (workflow pattern to copy) | `backend/app/scheduler.py` |
| HTTP API (inline closures, no APIRouter) | `backend/app/main.py` |
| ORM models (new tables only, `create_all`, no migrations) | `backend/app/models.py` |
| Frontend API client / types / nav | `frontend/lib/api.ts`, `frontend/lib/types.ts`, `frontend/components/sidebar.tsx` |
| Frontend page pattern to copy | `frontend/app/reports/page.tsx` |
| Test patterns (scripted model client) | `backend/tests/fake_anthropic.py`, `backend/tests/test_phase4.py`, `backend/tests/conftest.py` |

## Critical gotchas

- **Demo-mode markers**: `simulated.py` identifies an agent by the FIRST
  `_MARKERS` substring found in its system prompt. Any new/edited prompt must
  contain its agent's marker and must NOT contain any other marker string.
  There is a regression test for this
  (`tests/test_founder_memory.py::test_every_agent_prompt_resolves_to_its_own_demo_handler`).
- **Workflow briefs must start with a `TOPIC: <topic>` line** — demo-mode
  venture handlers parse it to produce readable canned output.
- **Running an agent programmatically** (the workflow pattern): see
  `scheduler.py` — `agent.run(task, on_event=<async noop>, budget=TokenBudget(limit=...))`;
  never go through chat/delegation for workflows.
- **Delegation depth is capped at 2** (`Settings.max_delegation_depth`); venture
  workflows call agents directly at depth 0, so don't add delegation chains.
- **Report kinds are free strings** but must be added to BOTH
  `frontend/lib/types.ts` (`ReportSummary.kind`) and `KIND_META` in
  `frontend/app/reports/page.tsx` when introduced.
- **SQLite `create_all` adds new tables only** — never alter existing table
  columns.
- **FakeClient dict mode** (tests): keys are system-prompt substrings (use the
  same marker strings), values are FIFO lists of scripted responses; an agent
  called twice needs two queued responses.

## Commands

```bash
# backend
cd backend
pip install -r requirements.txt
python3 scripts/seed.py                 # idempotent; --force to regenerate
python3 -m pytest                       # must be green before push
DEMO_MODE=1 python3 -m uvicorn app.main:app --port 8000   # zero-cost run

# frontend
cd frontend && npm install && npm run dev   # http://localhost:3000
npm run build                                # type-check gate
```

## Style

- Python: match the existing voice — module docstrings explaining *why*,
  sparse inline comments only for non-obvious constraints, f-strings,
  `from __future__ import annotations`, type hints on public functions.
- Prompts: follow `app/venture/agents.py` — role, method/principles, explicit
  required output format; no hype language.
- Tests: plain pytest, no new fixtures frameworks; reuse `conftest.py`
  fixtures (`settings`, `seeded_db`) and the `writable_settings` copy pattern.
- Commits: imperative subject, body explaining what and why, no attribution
  footers other than your own tool's defaults.

## Collaboration protocol (agreed between Claude and Codex)

Roles: **Claude** = lead architect/orchestrator — owns vision, architecture,
interfaces, data models, task sequencing, review, and integration. **Codex** =
implementation agent — implements task packets exactly, surfaces ambiguities
before guessing, writes/updates tests, runs validation, self-reviews its diff,
pushes, and addresses review findings. GitHub is the source of truth; never
rely on chat history alone.

### Branch ownership

- Claude owns the **integration branch: `claude/agent-operating-system-66e55h`**.
  (Note: `claude/ai-business-os-spec-kz8k5w` is a stale pre-venture branch at
  `101f683` — do NOT base work on it.)
- Codex owns `codex/<task-id>` branches, always created from the current tip
  of the integration branch.
- Never edit, reset, force-push, or rewrite the other agent's branch. Claude
  does not commit on `codex/*`; Codex does not commit on `claude/*`.
- Never implement the same task concurrently on both sides.
- Claude integrates accepted Codex commits into the integration branch
  (merge); trivial integration fixups happen as separate, labeled commits on
  the integration branch, never on Codex's branch.
- Per-phase reviews are BLOCKING-focused (structure/correctness gates only).
  At project end Claude runs a full audit-and-fix pass: complete verification,
  line-level review of all implementer-written code, and below-standard items
  fixed by Claude directly on the integration branch as labeled commits,
  documented in `docs/SYSTEMS_REPORT.md`.
- Never commit secrets, credentials, `.env` files, or private data.

### Task packets

Every implementation task gets a packet in `docs/tasks/` with these fields:
TASK ID, TITLE, BASE BRANCH, BASE COMMIT SHA, OBJECTIVE, ARCHITECTURAL
CONTEXT, FILES OR AREAS IN SCOPE, FILES OR AREAS OUT OF SCOPE, FUNCTIONAL
REQUIREMENTS, ACCEPTANCE CRITERIA, REQUIRED TESTS, SECURITY AND EDGE CASES,
CONSTRAINTS, DEPENDENCIES, KNOWN RISKS, EXPECTED DELIVERABLE. A packet may
delegate detail to a full spec file (`docs/tasks/V*-*.md`), which is then
normative.

### Review findings format (Claude → Codex, after each push)

```
BLOCKING:      (must fix before integration)
IMPORTANT:     (should fix; negotiable with justification)
OPTIONAL:      (nice to have)
ARCHITECTURAL VERDICT:
TESTING VERDICT:
ACCEPT / REQUEST CHANGES:
```

Review notes are committed to `docs/tasks/<task-id>-REVIEW.md` on the
integration branch (and relayed via the human). Codex addresses findings on
its own branch and pushes again. Integration happens only after all BLOCKING
findings are resolved and required tests pass.

### Ambiguity rule

Spec ambiguity? Choose the interpretation that touches the least existing
code, and record the decision in the commit message body.
