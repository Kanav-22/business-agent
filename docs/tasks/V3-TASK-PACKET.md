# TASK PACKET

TASK ID: V3

TITLE: Venture workflows (debate, failure sim, interviews, idea score) + REST triggers

BASE BRANCH: claude/agent-operating-system-66e55h

BASE COMMIT SHA: the tip of BASE BRANCH at task start (relayed in the chat
handoff; this packet's commit or later — verify with `git log -1 origin/claude/agent-operating-system-66e55h`)

OBJECTIVE: Give the venture layer its four multi-agent workflows so a founder
can run a board debate, a failure simulation, synthetic customer interviews,
and a strict idea scoring from one REST call each — at $0 in DEMO_MODE.

ARCHITECTURAL CONTEXT: Workflows are deterministic orchestration code over
prompt-driven agents ("agents think, code sequences/validates/persists").
They call agents directly with `agent.run(...)` (the `scheduler.py` pattern),
never through chat delegation. Reports go through `save_report`
(`app/api/reports.py`), memories through `save_memory_record`
(`app/api/venture.py`). The venture roster and demo-mode handlers already
exist (V2). Architecture docs: `AGENTS.md` (map + gotchas), `docs/AUDIT.md`,
`docs/MEMORY_SYSTEM.md`.

FILES OR AREAS IN SCOPE:
- `backend/app/venture/workflows.py` (new)
- `backend/app/main.py` (venture section only: two endpoints + one pydantic model)
- `backend/tests/test_venture_workflows.py` (new)

FILES OR AREAS OUT OF SCOPE: everything else — especially
`app/agents/service.py`, `app/agents/simulated.py`, existing endpoints,
existing tests, `docs/` design documents, frontend.

FUNCTIONAL REQUIREMENTS: normative detail in
`docs/tasks/V3-venture-workflows.md` (same directory). Summary: four async
workflows `run_debate` / `run_failure_simulation` / `run_customer_interviews`
/ `run_idea_score`, each `(service, engine, topic, *, on_event=None) -> int`
(report id); briefs start with `TOPIC: <topic>`; debate = venture_ceo proposal
→ 5 parallel critiques → researcher check → venture_ceo revision, report with
the fixed section headings; each workflow saves its report kind + memory
category; `VENTURE_WORKFLOWS` registry; `GET /api/venture/workflows` +
`POST /api/venture/{name}` (202/400/404/409 per spec).

ACCEPTANCE CRITERIA: the checklist at the end of
`docs/tasks/V3-venture-workflows.md`, plus: full pytest green; demo-mode
manual smoke produces 4 reports, 1 idea, and decision/risk/customer_research
memories.

REQUIRED TESTS: the six cases specified in the spec's §3 (FakeClient dict
mode keyed by marker strings; agent-failure resilience; API contract).

SECURITY AND EDGE CASES: workflows must never raise because one agent failed
(embed `[X unavailable: …]` instead); topic stripped, capped at 500 chars,
400 on empty; concurrency guard per workflow name (409); no raw SQL, no new
write paths — only `save_report`/`save_memory_record`/the score_idea tool.

CONSTRAINTS: `AGENTS.md` hard rules; no new dependencies; briefs must carry
the `TOPIC:` line; revision brief must contain the words "Revise" and
"objections"; do not touch the delegation system or depth limits.

DEPENDENCIES: V2 (merged — venture agents, demo handlers, persistence
helpers all exist on the base branch).

KNOWN RISKS: (1) demo-mode researcher returns an "needs API key" notice —
include it verbatim in the debate report, do not special-case it away;
(2) `run_idea_score` must tolerate the model not calling the tool (save a
"no idea was scored" report rather than crashing); (3) FakeClient queue
exhaustion raises AssertionError — script exactly the right number of
responses per agent.

EXPECTED DELIVERABLE: branch `codex/v3-workflows` pushed, containing the
implementation + tests, full suite green, one or more commits whose bodies
note any ambiguity decisions taken.
