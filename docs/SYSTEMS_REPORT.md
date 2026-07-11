# Systems Report — the 12 Operating-System Extensions

Final report for the venture-layer build. Companion documents:
`docs/AUDIT.md` (pre-build audit), `docs/ROADMAP.md` (phase log with
commits), `docs/tasks/*-REVIEW.md` (per-task review records),
`OS_TEMPLATE.md` (the reusable blueprint).

Built by two AI agents under the protocol in `AGENTS.md`: Claude
(architecture, docs, V1-V2, specs, reviews, integration) and Codex
(implementation of V3 workflows, V4 evals, V5a frontend). All three Codex
tasks were accepted with **zero blocking findings**; two of its ambiguity
decisions improved on the specs (idea attribution via tool-result events;
strong background-task references).

## 1. What already existed (and was not touched)

The Phase 1-4 operations layer: CEO orchestrator → CFO (FP&A/Reporting/
Revenue/Control), CMO (Content), CTO, Researcher, Coordinator over synthetic
SQLite data; guardrails (SELECT-only SQL, sandboxed calc, validated writes,
budgets, depth limits, JSONL logs); Approvals inbox; scheduled Monday jobs;
dashboard (Overview/Chat/Activity/Reports/Approvals); DEMO_MODE; 64 tests.
Its behavior is byte-identical by default — the original 64 tests still pass
unmodified (one endpoint test gained *additive* assertions).

## 2. The 12 systems: was → is

| # | System | Was | Is now |
|---|--------|-----|--------|
| 1 | Agent Evaluation System | plumbing tests only | `backend/evals/`: 18 scenario cases (2 per role × 9 roles incl. the ₹50,000/30-day founder case), deterministic 0-10 rubric, CLI runner, `eval_results` table, `GET /api/evals`, eval reports |
| 2 | Model Downgrade Survival Kit | missing | 9 guides in `docs/survival/` + `SURVIVAL_MODE=1` runtime injection (`app/agents/survival.py`) |
| 3 | Prompt Router | LLM-only routing | Deterministic 15-rule router (`app/venture/router.py`, mirror: `docs/ROUTING_RULES.md`), domain risk escalation, founder-fit notes, rejected-idea warnings, `POST /api/route` |
| 4 | Agent Debate System | missing | `run_debate` workflow: venture CEO proposes → CFO/CMO/CTO/COO/Risk attack in parallel → Researcher checks → CEO revises + decides; 9-section board report + decision memory |
| 5 | Business Failure Simulator | missing | `run_failure_simulation`: Red Team + Risk over 7/30/90/365-day horizons; report + risk memory |
| 6 | Red Team Agent | missing | `red_team` agent (weak assumption / why it matters / evidence / scenario / severity / fix / revised recommendation) |
| 7 | Synthetic Customer Interviews | missing | `run_customer_interviews`: 20 personas × 13 fields + synthesis, disclaimer enforced in code; customer-research memory |
| 8 | Founder Clone File | missing | `founder_profile` table (16 keys), `PUT/GET /api/founder`, editor UI, auto-prepended to every venture brief; template: `docs/FOUNDER_CLONE_TEMPLATE.md` |
| 9 | Memory System | implicit only | `memories` table, 16 categories with access matrix (`docs/MEMORY_SYSTEM.md`), validated `save_memory` tool with per-agent allowlists, workflow auto-saves, API + UI browser |
| 10 | Business Playbook Library | missing | 12 playbooks (`docs/playbooks/`), served via `GET /api/playbooks[/{slug}]`, rendered in the UI |
| 11 | Idea Scoring Engine | missing | 14-category strict engine (`app/venture/scoring.py`): model proposes scores, **code computes Go/No-Go/Test-First** (GO needs avg ≥7.5, no category ≤3, demand/fit/speed ≥6); `ideas` table, scoreboard UI |
| 12 | Execution Dashboard Schema | 10 tables, no doc | `docs/DASHBOARD_SCHEMA.md` mapping all 16 requested entities; 4 new tables (ideas, memories, founder_profile, eval_results); Venture Studio page as the command surface |

New agents: venture CEO/CFO/CMO/CTO (skeptics), COO, Risk Officer, Red Team,
Sales, Interviewer, Idea Scorer — all with demo-mode playbooks. "Board" is
the debate workflow, per `docs/survival/BOARD_AGENT_SURVIVAL_GUIDE.md`.

## 3. How to use each system (quick reference)

Everything below works at $0 with `DEMO_MODE=1`.

```bash
# Workflows (results appear in Reports and the Venture Studio page)
curl -X POST :8000/api/venture/debate      -d '{"topic":"Launch an AI tool for doctors"}' -H 'Content-Type: application/json'
curl -X POST :8000/api/venture/failure_sim -d '{"topic":"..."}' -H 'Content-Type: application/json'
curl -X POST :8000/api/venture/interviews  -d '{"topic":"..."}' -H 'Content-Type: application/json'
curl -X POST :8000/api/venture/idea_score  -d '{"topic":"..."}' -H 'Content-Type: application/json'

# Router (the doctor example returns primary=ceo, risk=high, Risk Officer added)
curl -X POST :8000/api/route -d '{"message":"I want to launch an AI tool for doctors."}' -H 'Content-Type: application/json'

# Founder clone / memories / ideas / playbooks
curl -X PUT :8000/api/founder -d '{"values":{"budget_range":"₹50,000"}}' -H 'Content-Type: application/json'
curl ':8000/api/memories?category=decision'   # + POST /api/memories/{id}/archive
curl :8000/api/ideas                          # + /api/ideas/{id}
curl :8000/api/playbooks                      # + /api/playbooks/{slug}

# Evals — the model-comparison loop
cd backend
DEMO_MODE=1 python3 -m evals.runner --save-report          # $0 smoke
AGENT_MODEL=<strong>  python3 -m evals.runner               # baseline
AGENT_MODEL=<weaker>  python3 -m evals.runner               # candidate
AGENT_MODEL=<weaker> SURVIVAL_MODE=1 python3 -m evals.runner # candidate + kit
```

Or use the **Venture Studio** page (`/venture`): run workflows, browse the
idea scoreboard, test the router, edit the founder profile, manage memories,
read playbooks, view eval results.

Example end-to-end (the spec's own scenario): set the founder profile
(₹50,000, 30 days, basic coding) → `idea_score` "AI automation business"
(demo verdict: TEST FIRST 5.5/10 — deliberately strict) → `interviews` for
message angles → `failure_sim` for the pre-mortem → `debate` for the final
go/no-go with owner, deadline, and reversal trigger. Every step leaves a
report and a memory the next step retrieves.

## 4. File inventory

- **New:** `docs/` (audit, roadmap, memory/routing/founder/schema designs,
  9 survival guides, 12 playbooks, 3 task specs + packets + 3 review
  records), `backend/app/venture/` (agents, scoring, router, founder,
  workflows), `backend/app/tools/{save_memory,score_idea}.py`,
  `backend/app/agents/survival.py`, `backend/app/api/venture.py`,
  `backend/evals/` (rubric, runner, 18 cases, README), 5 new test files,
  `frontend/app/venture/page.tsx`, `AGENTS.md`, `OS_TEMPLATE.md`.
- **Touched (additively):** `models.py` (+4 tables), `config.py` (+2
  settings), `service.py` (+venture roster, survival hook), `simulated.py`
  (+markers/handlers), `main.py` (+venture endpoints), `test_api.py`
  (superset assertion), `types.ts`/`sidebar.tsx`/reports `KIND_META`
  (+entries), `README.md` (+section).

## 5. Verification record

- 128/128 backend tests (64 pre-existing + 64 added across V2-V4).
- Frontend production build green, `/venture` route at 11 kB.
- Live DEMO_MODE server smoke: all four workflows, router, playbooks,
  founder roundtrip, memories, eval run (18 cases, report persisted).
- Regression: demo chat "How is the business doing?" still fans out
  CFO/CMO/CTO/Coordinator exactly as in Phase 4.
- Final audit-and-fix pass (per `AGENTS.md`): line-level review of all
  implementer code found zero blocking issues across three tasks; the
  OPTIONAL notes are recorded in the review files and none met the
  below-standard bar for direct fixes.

## 6. What still needs future improvement

1. **Real-model eval baselines** — the demo scoreboard is a smoke test;
   run the runner against the live strong model to record the baseline
   before you lose access to it (one command, see §3).
2. Embedding-based memory retrieval (design in `docs/MEMORY_SYSTEM.md`);
   category+recency retrieval is fine below a few hundred records.
3. Optional LLM-judge eval mode alongside the structural rubric.
4. `businesses` / `experiments` / `meetings` tables when the OS runs
   multiple ventures (`docs/DASHBOARD_SCHEMA.md` §C), plus Phase 5 of the
   original spec (real data providers, multi-tenant, Postgres).
5. An evals dashboard page (results are API-only + a table in Venture
   Studio today); friendlier case labels.
6. `VENTURE_IN_CHAT=1` is off by default — consider enabling once you've
   used the venture agents enough to trust them in the chat roster.
7. Split `frontend/app/venture/page.tsx` (1,223 lines) into section
   components if it grows further.
