# Roadmap — AI Business OS, venture layer and beyond

Integration branch: `claude/agent-operating-system-66e55h`. One task packet
per phase in `docs/tasks/`; protocol in `AGENTS.md`.

| Phase | Scope | Owner | Status |
|-------|-------|-------|--------|
| V1 | Documentation library (audit, 9 survival guides, 12 playbooks, memory/routing/founder/schema designs) | Claude | **Done** (`5d0b3c2`) |
| V2 | Backend foundations: 4 tables, 10 venture agents, scoring engine, router, founder clone, memory store, survival mode, demo playbooks, 10 REST endpoints | Claude | **Done** (`e4f8af5`), 85/85 tests |
| V3 | Venture workflows (debate, failure sim, interviews, idea score) + REST triggers | **Codex** (packet `V3`), Claude reviews | **Done** — implemented by Codex (`0fb4bb2`), ACCEPTED (`docs/tasks/V3-REVIEW.md`), merged; 97/97 tests |
| V4 | Evaluation system (cases, rubric, runner, README) | **Codex** (packet `V4` after V3 merges), Claude reviews | Spec ready — `docs/tasks/V4-evaluation-system.md` |
| V5a | Venture Studio frontend + README section | **Codex** (packet `V5` after V3 merges; parallel with V4) | Spec ready — `docs/tasks/V5-frontend-venture-studio.md` |
| V5b | `OS_TEMPLATE.md` (reusable OS blueprint) + `docs/SYSTEMS_REPORT.md` (final report) | Claude | After V3+V4 merge |
| Final | **Claude's full audit-and-fix pass**: complete suite + demo end-to-end verification, line-level review of all Codex-written code, below-standard items fixed by Claude directly as labeled commits on the integration branch, findings documented in `docs/SYSTEMS_REPORT.md`; then push | Claude (Codex reviews the result) | Last |

## Sequencing rules

- V4 and V5a touch disjoint files and may run as parallel Codex tasks once V3
  is merged (V4's `board` eval case and V5a's workflow buttons both need V3's
  endpoints/workflows).
- Nothing may regress the operations layer: the original 64 tests are the
  floor, `AGENTS.md` hard rules apply to every task.

## Post-V (future, not scheduled)

- Phase 5 of the original spec: `RealBusinessProvider` (CSV/Stripe),
  multi-tenant auth, Postgres.
- Embedding-based memory retrieval (design in `docs/MEMORY_SYSTEM.md`).
- Eval LLM-judge mode; eval dashboard page.
- `businesses`/`experiments`/`meetings` tables (design in
  `docs/DASHBOARD_SCHEMA.md` §C).
