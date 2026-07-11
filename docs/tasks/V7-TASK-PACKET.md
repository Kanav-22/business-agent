# TASK PACKET

TASK ID: V7

TITLE: Business Intake — guided owner interview, uploads, business context injection

BASE BRANCH: claude/agent-operating-system-66e55h (AFTER V6 is merged)

BASE COMMIT SHA: tip of BASE BRANCH at task start (see chat handoff)

OBJECTIVE: The OS interviews the business owner in the frontend (structured
questions + own-words narratives), collects the uploads it needs, stores a
durable Business Profile, injects it as context into chat and every venture
workflow, and runs an analyst review that writes what the team learned to
memory — so every agent operates with full knowledge of the real business.

ARCHITECTURAL CONTEXT: generalizes the Founder Clone pattern
(`app/venture/founder.py`) from the person to the business. "Learning" =
context engineering (profile + memories + brief injection), NOT model
training. Normative spec: `docs/tasks/V7-business-intake.md`.

FILES OR AREAS IN SCOPE: `backend/app/models.py` (BusinessProfile, append),
`backend/app/venture/intake.py` (new), `backend/app/venture/workflows.py`
(`_brief` + `intake_review` + registry), `backend/app/agents/service.py`
(`ask_ceo` context wrap ONLY), `backend/app/main.py` (venture section),
`backend/tests/test_intake.py` (new), `frontend/app/onboarding/page.tsx`
(new), `frontend/components/sidebar.tsx` / `frontend/lib/types.ts` /
`frontend/app/reports/page.tsx` KIND_META (append).

FILES OR AREAS OUT OF SCOPE: operations agents' static prompts (the Lumina
context swap is V8), founder.py, router.py, evals, everything else.

FUNCTIONAL REQUIREMENTS: per the spec — the exact question set (including
the two required own-words questions), upload manifest (.csv → staged for
the V6 importer, .txt/.md → intake reports), `business_context()` contract,
chat wrap that is byte-identical no-op on an empty profile, the
`intake_review` parallel workflow with its three deterministic memory
saves, the questions-driven wizard with autosave.

ACCEPTANCE CRITERIA: spec checklist; full pytest + `npm run build` green;
DEMO_MODE end-to-end (wizard → upload → review → context-aware chat).

REQUIRED TESTS: spec §7 list.

SECURITY AND EDGE CASES: upload extension/size/filename sanitization; no
auto-import of partial CSV sets; profile values capped; empty-profile paths
byte-identical (regression-tested); history stores the original message,
not the context-wrapped one.

CONSTRAINTS: AGENTS.md hard rules; frontend renders questions from the API
(no hardcoded question text); at most one new dependency
(`python-multipart` IF genuinely missing, noted in commit body).

DEPENDENCIES: V6 merged (upload step references the importer + templates).

KNOWN RISKS: context block bloating chat token usage on long profiles (caps
mitigate); marker-safety — intake.py strings must not contain demo marker
phrases (regression test exists); double-injection if a venture brief and
chat wrap ever combine (they don't share a path — keep it that way).

EXPECTED DELIVERABLE: branch `codex/v7-intake` pushed, suite + build green,
ambiguity decisions in the commit body.
