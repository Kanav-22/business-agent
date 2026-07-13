# Task V9 — Dynamic company context for the operations layer

**Branch:** `codex/v9-company-context` (from latest
`claude/agent-operating-system-66e55h`)
**Read first:** `AGENTS.md`, `backend/app/agents/service.py` (all prompt
constants), `backend/app/venture/intake.py` (`get_business_profile`),
`backend/app/agents/simulated.py` (`_MARKERS` — the load-bearing strings),
`backend/tests/fake_anthropic.py` (dict mode keys on marker substrings).

## Goal

Today every operations prompt hardcodes "Lumina Labs, a 12-person B2B SaaS
analytics company…". After V6 (real data import) and V7 (business intake),
that text is wrong the moment a real business is loaded. V9 makes the
company context in the operations prompts come from the stored business
profile when one exists — and stay **byte-identical to today when it
doesn't**.

## 1. Context source — `company_context_line(engine)` in `app/venture/intake.py`

Returns a one-sentence company descriptor:

- Profile has a non-empty `name`: build
  `"{name}. {first ~200 chars of description_own_words, sentence-truncated}"`
  — normalized to end with a period, single line, max 300 chars. Fields
  used: `name`, `description_own_words` (fallback to `pricing_summary`
  appended only if description is empty and pricing is short).
- Otherwise: return the exact current default string
  (`"Lumina Labs, a 12-person B2B SaaS analytics company (plans: starter
  $99, growth $299, scale $899 per month)."`) — move that literal into ONE
  constant (`DEFAULT_COMPANY_CONTEXT`) exported from `intake.py` and
  imported by `service.py`; the string itself must not change.

## 2. Prompt refactor — `app/agents/service.py`

The prompt constants are module-level f-strings baked at import time.
Convert them to **builder functions** parameterized by the company context,
with backward-compatible module constants:

```python
def build_fpa_prompt(company: str) -> str: ...
FPA_SYSTEM_PROMPT = build_fpa_prompt(DEFAULT_COMPANY_CONTEXT)   # unchanged export
```

Rules:

- EVERY marker string in `simulated._MARKERS` must remain verbatim in its
  prompt for ANY company value ("You are the CFO", "CMO agent",
  "Workflow Coordinator", …). The CFO and CEO prompts hardcode
  "Lumina Labs, a 12-person B2B SaaS analytics company" in prose — replace
  with the parameter, but keep the marker prefixes intact
  ("You are the CFO agent of {company} You lead…" — note the existing
  no-comma style after the context sentence; preserve exactly).
- `AgentService.__init__` computes
  `company = company_context_line(self.engine)` once (guard with
  try/except → default, so a missing/locked DB can never break
  construction) and builds operations prompts from it. Venture prompts are
  untouched (they already get business context per brief).
- Company context is applied at construction: a profile saved via the
  intake wizard takes effect on backend restart. Document this in the
  intake page's finish step? NO frontend changes in this task — instead
  append one sentence to `docs/CONNECT_REAL_BUSINESS.md` and the README's
  venture section: "operations agents pick up the business profile at
  backend startup — restart after completing intake."
- The chat `BUSINESS CONTEXT` wrap from V7 stays as-is (it carries the
  FULL profile per message; the prompt line is the short identity).

## 3. Scheduler/report titles

`scheduler.py` job briefs/titles that say "Lumina Labs" (if any — check)
switch to the same `company` value captured at service construction; report
KINDS and function names unchanged.

## 4. Tests — extend `backend/tests/test_intake.py` (or a new `test_company_context.py`)

1. **Byte-identical default**: with an empty business profile, every agent's
   `config.system_prompt` equals the prompt built with
   `DEFAULT_COMPANY_CONTEXT` — assert equality against the exported legacy
   constants for at least fpa/cfo/cmo/cto/coordinator/content/ceo.
2. **Real profile**: set `name` + `description_own_words`, build a fresh
   `AgentService` → cfo/cmo/cto prompts contain the business name and NOT
   "Lumina Labs"; CEO prompt likewise.
3. **Marker invariance**: the existing parametrized marker-resolution test
   must pass in BOTH profile states — extend it with a fixture param that
   sets a profile (this is the regression that matters most).
4. `company_context_line`: default fallback exact-match; truncation at 300;
   single-line normalization; DB-error fallback (monkeypatch
   `get_business_profile` to raise → default returned).
5. FakeClient dict-mode keys still route (implicitly covered by 3 — do not
   change any marker or test key).

## Constraints

`AGENTS.md` hard rules. Files: `service.py`, `intake.py`, `scheduler.py`
(only if it embeds the company name), the two doc sentences, tests. No
frontend, no new deps, no prompt-content changes beyond the company
sentence substitution, no changes to demo-mode handlers.

## Known risks

- Prompt drift breaking demo mode or FakeClient routing → the marker
  invariance test is the gate; run the FULL suite, not just new tests.
- Subtle whitespace changes during the constant→builder refactor → the
  byte-identical test catches this; build it FIRST.
- A hostile/odd profile value injected into prompts (the owner controls it,
  but sanitize anyway): strip newlines, cap length, no other filtering.

## Acceptance checklist

- [ ] Full pytest green (168 + new).
- [ ] DEMO_MODE manual: with no profile, chat behaves exactly as today;
      after saving a profile with a distinct name and restarting, the CFO's
      answer attributes to the real company name (demo canned text includes
      the system-prompt-derived identity only where it already would).
- [ ] Byte-identical-default test present and passing.
