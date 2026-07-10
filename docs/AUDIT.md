# Product Audit — 12 Operating-System Extensions vs. the Existing Product

Audited on the Phase 4 codebase (commit `101f683`). This document records what already
existed, what was partial, what was missing, and the safe implementation plan that the
Venture layer followed. Nothing that existed before this audit was removed or rewritten.

## 1. Already implemented (before this work)

- **Multi-agent core**: one `Agent` class, many configs (`backend/app/agents/base.py`);
  CEO orchestrator → CFO (FP&A/Reporting/Revenue/Control), CMO (Content), CTO,
  Researcher, Coordinator (`backend/app/agents/service.py`).
- **Guardrails**: SELECT-only SQL with per-agent table allowlists, sandboxed
  `python_calc`, validated write tools (`create_task`, `report_writer`,
  `content_writer`), token budget, delegation-depth limit, JSONL decision logging.
- **Human-in-the-loop**: Approvals inbox — outward content never publishes without a click.
- **Scheduled operations**: Monday control check, CEO briefing, competitor scan.
- **Dashboard**: Overview, Chat (live delegation tree), Agent Activity, Reports, Approvals.
- **DEMO_MODE**: zero-cost simulated model with rule-based routing and real tool execution.
- **Plumbing test suite**: 64 tests with a scripted fake Anthropic client.

## 2. Status of the 12 requested systems

| # | System | Status before | Notes |
|---|--------|---------------|-------|
| 1 | Agent Evaluation System | **Partially present** | pytest verified *plumbing* (delegation, guardrails), never *output quality* — no scenarios, rubrics or pass/fail |
| 2 | Model Downgrade Survival Kit | **Missing** | Prompts encoded some structure (`_GROUNDING_RULES`), no per-agent guides |
| 3 | Prompt Router | **Partially present** | CEO routes via LLM judgment; demo mode keyword routing; no explicit rule table with risk levels/workflows/reasons |
| 4 | Agent Debate System | **Missing** | — |
| 5 | Business Failure Simulator | **Missing** | — |
| 6 | Red Team Agent | **Missing** | Control agent is a skeptic for data reconciliation only |
| 7 | Synthetic Customer Interviews | **Missing** | — |
| 8 | Founder Clone File | **Missing** | — |
| 9 | Memory System Design | **Partially present** | Implicit memory only (SQLite data, Reports library, JSONL logs, 8-message chat history) |
| 10 | Business Playbook Library | **Missing** | — |
| 11 | Idea Scoring Engine | **Missing** | — |
| 12 | Execution Dashboard Schema | **Partially present** | 10 ORM models existed; no schema design doc; no ideas/memories/founder/eval tables |

Agents referenced by the 12 systems that did not exist: **COO, Risk Officer, Sales,
Red Team, Interviewer**. "Board" maps to the debate workflow (documented as such).

## 3. Missing (added by the Venture layer)

Survival guides, playbooks, memory design + memory records, founder clone, routing
rule table, debate workflow, failure simulator, red-team agent, synthetic interviews,
idea scoring engine, output-quality evals, dashboard schema doc, OS template.

## 4. Recommended additions (and what was deliberately skipped)

Added: everything above, as a modular **venture layer** beside the untouched
operations layer. Skipped, documented as future work: vector/embedding memory
retrieval; LLM-as-judge as the *default* eval mode (optional flag instead); venture
agents inside the live CEO chat roster by default (opt-in `VENTURE_IN_CHAT=1`);
database tools for Sales/COO (prompt-only suffices).

## 5. Files added / updated

See `docs/SYSTEMS_REPORT.md` for the full inventory. Existing files were touched only
at additive wiring points: `service.py` (venture roster construction), `simulated.py`
(new markers/handlers appended), `main.py` (new endpoints), `models.py` (new tables),
`config.py` (new settings), `sidebar.tsx` / `types.ts` / reports `KIND_META`
(appended entries), `README.md` (new section).

## 6. Risk of breaking the existing product

Low, by construction:

- Only **new** tables (SQLite `create_all` adds them automatically; existing tables
  are never altered).
- The CEO chat roster is unchanged by default, so live and demo chat behavior is
  identical to Phase 4 unless `VENTURE_IN_CHAT=1` is set.
- Survival-mode prompt injection is off by default (`SURVIVAL_MODE=1` to enable).
- Every phase kept the pre-existing 64 tests green.

## 7. Safe implementation plan (as executed)

1. **V1 — docs only** (this directory): zero runtime risk.
2. **V2 — backend foundations**: new models, venture agents, scoring engine, router,
   founder profile, memory tool, survival mode, demo handlers, APIs, tests.
3. **V3 — workflows**: debate, failure simulator, interviews, idea scoring; venture
   API; demo-mode end-to-end; tests.
4. **V4 — evaluation system**: cases, rubric, runner, API, tests.
5. **V5 — frontend Venture Studio page, `OS_TEMPLATE.md`, final report, README.**

Full `pytest` after every phase; one commit per phase.
