# TASK PACKET

TASK ID: V9

TITLE: Dynamic company context — operations agents speak about the real business

BASE BRANCH: claude/agent-operating-system-66e55h

BASE COMMIT SHA: tip of BASE BRANCH at task start
(`git log -1 origin/claude/agent-operating-system-66e55h`; `69eedb3` at
packet creation)

OBJECTIVE: Replace the hardcoded "Lumina Labs…" identity inside the
operations agents' prompts with the stored business profile's identity when
one exists — while remaining provably byte-identical to today when it
doesn't.

ARCHITECTURAL CONTEXT: The last hardcoded piece of the demo company. V6
loads real data, V7 stores the real identity; V9 joins them. Normative
spec: `docs/tasks/V9-company-context.md`. The demo-mode marker strings and
FakeClient dict keys are the load-bearing invariants.

FILES OR AREAS IN SCOPE: `backend/app/agents/service.py` (prompt
constants → builder functions + construction-time context),
`backend/app/venture/intake.py` (`company_context_line`,
`DEFAULT_COMPANY_CONTEXT`), `backend/app/scheduler.py` (only if it embeds
the company name), one-sentence doc notes in
`docs/CONNECT_REAL_BUSINESS.md` + README venture section, tests.

FILES OR AREAS OUT OF SCOPE: frontend; venture prompts; demo-mode handlers;
`_MARKERS`; tools; workflows; everything else.

FUNCTIONAL REQUIREMENTS: per spec — context line construction with exact
default fallback, builder-function refactor with legacy constant exports,
construction-time application with DB-error fallback, newline-strip/length
cap sanitization.

ACCEPTANCE CRITERIA: spec checklist; the byte-identical-default test and
the both-profile-states marker-invariance test are mandatory and must be
written FIRST.

REQUIRED TESTS: spec §4 list.

SECURITY AND EDGE CASES: profile values are owner-controlled but still
sanitized (single line, capped); service construction must never fail on a
broken DB (fallback to default context).

CONSTRAINTS: AGENTS.md hard rules; no new dependencies; zero prompt-content
changes beyond the company-sentence substitution.

DEPENDENCIES: V7 merged (business profile exists) — satisfied.

KNOWN RISKS: whitespace drift during the refactor (caught by the
byte-identical test); marker breakage (caught by the extended marker test);
scheduler job briefs embedding stale identity (check `scheduler.py`
explicitly and say in the commit body whether changes were needed).

EXPECTED DELIVERABLE: branch `codex/v9-company-context` pushed, full suite
green, ambiguity decisions in the commit body.
