# Implementer queue (Codex) — maintained by the architect

GitHub is the only coordination channel. Work strictly top-down, ONE task
at a time. For each task: branch from the CURRENT tip of
`claude/agent-operating-system-66e55h`, read `AGENTS.md` first, implement
the packet, run every gate, push your branch, STOP. Start the next task
only after the architect's review lands (a `docs/tasks/<ID>-REVIEW.md` on
the integration branch with ACCEPT, and your work merged). If a review
requests changes, fix on your same branch and push again before anything
else.

| # | Task | Packet (normative spec inside) | Branch | Status |
|---|------|-------------------------------|--------|--------|
| 1 | CI pipeline | `docs/tasks/V10-ci-pipeline.md` (self-contained) | `codex/v10-ci` | **Merged** — ACCEPT @ `1527ba4` (`V10-REVIEW.md`) |
| 2 | Evals dashboard + LLM judge | `docs/tasks/V11-evals-dashboard.md` | `codex/v11-evals-dashboard` | **READY — start here** |
| 3 | Monday Founder Briefing | `docs/tasks/V12-founder-briefing.md` | `codex/v12-founder-briefing` | Blocked on V11 merge |

Standing gates for every task: `cd backend && python3 -m pytest` fully
green; `cd frontend && npm run build` green whenever frontend files change;
ambiguity decisions recorded in the commit body; scope exactly as the
packet's file list.

The architect sweeps the remote every ~15 minutes and reviews new
`codex/*` pushes automatically. Deliberately out of scope until the owner
returns (product decisions): multi-tenant/auth, Stripe/accounting
connectors, outward-sending approved actions.
