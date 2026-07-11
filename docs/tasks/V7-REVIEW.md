# Review — Task V7 (`codex/v7-intake` @ `c31c9e9`)

Reviewer: Claude (architect). Verified on a test merge against integration
tip `e772013`.

## Verification performed

- Scope: exactly the packet's file list; the one permitted dependency
  (`python-multipart`) added with justification. 1,883 insertions.
- Full backend suite on the merged tree: **168/168** (159 + 9 new intake
  tests). Frontend production build green (`/onboarding` at 8.4 kB).
- Live demo smoke: 24 questions across 8 sections served by the API
  (both required own-words questions present); business profile saved;
  `.md` upload became an intake report while a bad extension got 400;
  `intake_review` produced the three-section report AND the three memories
  in the correct categories (financial_assumption / customer_research /
  risk) linked to the business name; chat received the BUSINESS CONTEXT
  wrap with the profile set and completed without error.
- Marker safety: no demo-marker phrases in intake.py (checked all 21
  markers); the parametrized marker regression test passes.
- Empty-profile regression: `ask_ceo` passes the message through unchanged
  (byte-identical path), and history stores the original message (handled
  in main.py, untouched).

## Findings

BLOCKING: none.

IMPORTANT: none.

OPTIONAL:
1. `run_intake_review` lists prior `intake` reports in its brief — which,
   on repeat runs, includes previous *review* reports (self-referencing
   accumulation). Arguably useful context; consider filtering titles
   starting with "Business intake review:" if briefs bloat.
2. The upload endpoint canonicalizes CSV names (`transactions_csv` →
   `transactions.csv`) — good; the returned `next` hint could also mention
   `--db` for non-default databases. Cosmetic.

ARCHITECTURAL VERDICT: Conforms. The founder-clone pattern generalized
cleanly; context injection is additive at both seams (workflow briefs and
the chat wrap) and provably inert when the profile is empty; uploads never
auto-import partial CSV sets, exactly per spec.

TESTING VERDICT: Meets spec with good depth (question-set integrity,
context wrap + history behavior, upload validation matrix, workflow +
memory categories). Implementer additionally reported accessibility work
(keyboard focus, reduced motion) beyond the spec's requirements.

ACCEPT / REQUEST CHANGES: **ACCEPT** — merged into
`claude/agent-operating-system-66e55h`. Codex: 5 for 5, zero blocking
findings across the collaboration.
