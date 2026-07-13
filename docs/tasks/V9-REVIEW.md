# Review — Task V9 (`codex/v9-company-context` @ `3c1b19b`)

Reviewer: Claude (architect). Verified on a test merge against integration
tip `2d2800f`.

## Verification performed

- Scope: exactly the packet's files; existing-test edits were the
  spec-sanctioned ones, and both were STRENGTHENED (the competitor-scan
  test now proves profile adoption; the marker test is parametrized across
  profile × survival states and upgraded to assert a UNIQUE marker match).
- Full suite on the merged tree: **174/174** (168 + 6 new).
- **Independent byte-identity check**: I hashed every agent's system prompt
  on the pre-merge tree and on the merged tree with an empty profile — all
  21 prompts hash-identical. (Codex separately froze pre-refactor SHA-256s
  in the test suite; two independent methods, same result.)
- Live profiled check: with a saved business profile, a fresh service's
  CFO prompt contains the business identity and no "Lumina Labs";
  `company_context_line` produced a clean sentence-truncated one-liner;
  `service.company_context` exposed for the scheduler.
- Scheduler audit confirmed: the competitor-scan brief's two stale identity
  references now use the construction-captured context; legacy constant
  export preserved.

## Findings

BLOCKING: none.

IMPORTANT: none.

OPTIONAL:
1. Context applies at construction; a saved profile needs a backend restart
   (documented in README + CONNECT_REAL_BUSINESS per spec). A
   rebuild-service admin endpoint is a candidate for a future task.
2. `_description_prefix` strips trailing punctuation then re-adds a period
   — slightly convoluted but correct and tested.

ARCHITECTURAL VERDICT: Conforms. Builder-function refactor with exact
legacy exports; DB-failure fallback to the default context guards service
construction; sanitization (single-line, 300-char cap) applied to
owner-controlled values before prompt embedding.

TESTING VERDICT: Exceeds spec — frozen-hash byte-identity tests, four-way
parametrized marker invariance with uniqueness assertion, sentence-boundary
truncation cases, DB-error fallback.

ACCEPT / REQUEST CHANGES: **ACCEPT** — merged into
`claude/agent-operating-system-66e55h`. Codex: 7 for 7, zero blocking
findings. The operations layer now speaks about the owner's real business.
