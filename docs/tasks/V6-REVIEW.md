# Review — Task V6 (`codex/v6-real-data` @ `79b141d`)

Reviewer: Claude (architect). Verified on a test merge against integration
tip `296ef17`.

## Verification performed

- Scope: exactly the in-scope files (provider, CLI, templates + README,
  tests + fixtures). 1,981 insertions, zero deletions, no API/frontend/agent
  changes.
- Full suite on the merged tree: **159/159 passed** (129 + 30 new).
- Manual smoke: CLI import of the fixture directory into a scratch DB
  (row counts + window printed), `--check` dry-run produced all-`[OK]`
  reconciliation lines, and `get_kpis` returned correct real-data KPIs
  (MRR 1,000 / 5 active customers / cash 68,370).

## Findings

BLOCKING: none.

IMPORTANT: none.

OPTIONAL:
1. `check(engine)` accepts and immediately `del`s its engine argument — a
   slightly odd signature kept for interface symmetry; fine.
2. Reconciliation lines use exact-cent comparison; a tolerance flag could be
   useful for messy books later. `check()` correctly never blocks on
   `[WARN]`s, so this is cosmetic.

ARCHITECTURAL VERDICT: Conforms, with two above-spec choices worth noting:
(a) money is parsed as `Decimal` end-to-end (canonical two-decimal
enforcement, rejection of unrepresentable values) instead of floats — better
than the spec asked; (b) parse-everything-before-any-write means a failed
import provably leaves prior data intact (pinned by test). Force semantics
delete business tables in FK-safe order and preserve every artifact table.

TESTING VERDICT: Exceeds spec — 24 tests including UTF-8 BOM handling,
case-insensitive name FK resolution, artifact-only databases importing
without force, ambiguous/duplicate invoice matching, error-cap behavior
(≤20, no partial writes), and a check-writes-nothing filesystem assertion.

ACCEPT / REQUEST CHANGES: **ACCEPT** — merged into
`claude/agent-operating-system-66e55h`. Codex is now 4 for 4 with zero
blocking findings.
