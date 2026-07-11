# Task V6 — RealBusinessProvider (CSV import for real business data)

**Branch:** `codex/v6-real-data` (from latest `claude/agent-operating-system-66e55h`)
**Read first:** `AGENTS.md`, `docs/CONNECT_REAL_BUSINESS.md` (the manual path
this task productizes), `backend/app/data/provider.py` + `synthetic.py` (the
interface and its only implementation), `backend/app/models.py` (schema and
conventions), `backend/tests/test_reconciliation.py`.

## Goal

A validated CSV importer implementing the same `DataProvider` interface as
the synthetic generator, so a real business's exports load into the schema
with line-numbered errors instead of silent corruption. Library + CLI only —
no API endpoint, no frontend (V7's onboarding wizard will call the library).

## 1. `backend/app/data/real.py`

`class RealBusinessProvider(DataProvider)` with `__init__(source_dir: Path)`.

- **Required files:** `transactions.csv`, `customers.csv`, `meta.csv`.
  **Optional:** `invoices.csv`, `campaigns.csv`, `projects.csv`,
  `employees.csv`, `tasks.csv` — absent file = empty table, with a warning
  in the summary naming the agents that lose grounding (no invoices →
  Revenue agent blind, etc.).
- **Canonical headers** (case-insensitive, order-free), matching
  `docs/templates/*.csv` exactly. Unknown or missing headers → error before
  any row is read.
- **Row validation** collects errors as `filename:line: message` and aborts
  the import listing up to 20 of them (never partial-writes): ISO dates,
  positive amounts, enums per `models.py` docstrings (`type`, `category`,
  `plan`, `status` fields), `churn_date`/`due_date` ordering sanity.
- **FK resolution by name:** `transactions.customer_name` /
  `employee_name` / `campaign_name` columns (all optional per row) resolve
  against the imported entity tables; unresolvable name → row error.
- **Invoice ↔ transaction linking** (`Invoice.transaction_id` is NOT NULL):
  match each invoice to a revenue transaction by (customer, amount ± 0.01,
  issue_date); unmatched or doubly-matched → row error.
- **Meta:** `meta.csv` requires `starting_cash`; the importer computes
  `window_start`/`window_end` from the data and stamps `generated_at`
  (which marks the DB provisioned — see `provider.py:is_provisioned`).
- **Safety:** refuses a target DB that already has business rows unless
  `force=True`; `force` deletes business tables but NEVER touches
  artifacts (reports, memories, ideas, approvals, founder/business
  profiles, eval_results).
- `provision(engine, force=False) -> dict` returns
  `{"tables": {name: rowcount}, "window": [start, end], "warnings": [...]}`.
- `check(engine=None) -> dict` — dry-run: full validation plus a
  reconciliation preview (per-month subscription revenue vs. active-customer
  MRR sums; payroll vs. salaries/12; campaign spend vs. marketing
  transactions) returned as `[OK]/[WARN]` lines, writing nothing.

## 2. `backend/scripts/import_real.py`

CLI mirroring `scripts/seed.py` style:
`python3 scripts/import_real.py --source <dir> [--db <path>] [--check] [--force]`.
Prints the summary (or the error list) human-readably; exit 1 on validation
failure. `--db` defaults to the `BUSINESS_AGENT_DB` env or the standard path.

## 3. `docs/templates/`

One template per CSV with the canonical header row + 2 example rows, plus
`docs/templates/README.md` explaining each column, the enums, the
name-based FK columns, and the invoice-matching rule. These templates are
the contract; keep them in lockstep with the importer.

## 4. Tests — `backend/tests/test_real_provider.py`

Fixture CSVs under `backend/tests/fixtures/real_csv/` (tiny — ~6 customers,
2 months of transactions, reconcilable). Cover: happy import (rowcounts,
meta keys, KPIs positive via `get_kpis`); missing required file; bad header;
bad enum row (error carries filename:line); unmatched invoice; FK to
unknown customer; refusal without `force` on a provisioned DB + artifacts
surviving `force=True`; `check()` returning `[OK]` lines on the fixture and
writing nothing.

## Constraints & risks

- `AGENTS.md` hard rules; pandas is NOT available — use `csv` from the
  stdlib.
- Do not modify `synthetic.py`, `provider.py` semantics, or any agent/
  workflow code. `real.py` may add small shared helpers ONLY inside itself.
- Known risk: real books won't reconcile — that is expected; `check()`
  reports it, the importer must not block on `[WARN]`s (only on structural
  row errors).

## Acceptance checklist

- [ ] Full pytest green (129 existing + new).
- [ ] Manual: import the fixture dir into a scratch DB, start the server
      against it, `/api/kpis` returns the fixture's numbers; ask-the-CFO
      demo query grounds in them.
- [ ] Files touched only: `backend/app/data/real.py`,
      `backend/scripts/import_real.py`, `docs/templates/**`,
      `backend/tests/test_real_provider.py` + fixtures.
