# TASK PACKET

TASK ID: V6

TITLE: RealBusinessProvider — validated CSV import for real business data

BASE BRANCH: claude/agent-operating-system-66e55h

BASE COMMIT SHA: tip of BASE BRANCH at task start (see chat handoff;
`git log -1 origin/claude/agent-operating-system-66e55h`)

OBJECTIVE: Let a real business load its exports (transactions, customers,
invoices, …) into the OS with line-numbered validation errors, implementing
the same `DataProvider` interface as the synthetic generator — the agents
must not be able to tell the difference.

ARCHITECTURAL CONTEXT: `app/data/provider.py` defines the interface;
`app/data/synthetic.py` is the only implementation; `docs/
CONNECT_REAL_BUSINESS.md` documents the manual path this productizes.
Normative spec: `docs/tasks/V6-real-business-provider.md`.

FILES OR AREAS IN SCOPE: `backend/app/data/real.py` (new),
`backend/scripts/import_real.py` (new), `docs/templates/**` (new),
`backend/tests/test_real_provider.py` + `backend/tests/fixtures/real_csv/`
(new).

FILES OR AREAS OUT OF SCOPE: everything else — no API endpoints, no
frontend, no changes to synthetic.py/provider.py/agents/workflows.

FUNCTIONAL REQUIREMENTS: per the spec — canonical headers, collected
`file:line` errors (abort listing ≤20, never partial-write), name-based FK
resolution, invoice↔transaction matching (amount ±0.01 + customer + date),
required meta (`starting_cash`; window computed; `generated_at` stamped),
`force` semantics that never touch artifact tables, `check()` dry-run with
reconciliation preview, CLI with `--source/--db/--check/--force`.

ACCEPTANCE CRITERIA: spec checklist; full pytest green; fixture-dir manual
import serves real KPIs.

REQUIRED TESTS: spec §4 list.

SECURITY AND EDGE CASES: stdlib `csv` only (no pandas); refuse provisioned
DBs without force; artifacts survive force; malformed UTF-8 and empty files
are row-zero errors, not crashes.

CONSTRAINTS: AGENTS.md hard rules; no new dependencies.

DEPENDENCIES: none beyond the current integration branch.

KNOWN RISKS: real books won't reconcile — `check()` reports `[WARN]`s and
the importer must not block on them (only structural errors block); invoice
matching ambiguity (two identical charges same day) must error, not guess.

EXPECTED DELIVERABLE: branch `codex/v6-real-data` pushed, suite green,
ambiguity decisions in the commit body.
