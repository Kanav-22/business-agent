# Task V7 — Business Intake: guided interview, uploads, and business context

**Branch:** `codex/v7-intake` (from the integration branch AFTER V6 merges —
the upload step calls V6's importer).
**Read first:** `AGENTS.md`, `backend/app/venture/founder.py` (the pattern
this generalizes), `backend/app/venture/workflows.py` (`_brief`, registry),
`backend/app/api/venture.py`, `frontend/app/venture/page.tsx` (form/section
patterns), `docs/tasks/V6-real-business-provider.md`.

## Goal

The OS interviews the business owner in the frontend — structured questions
plus **own-words narrative answers** — collects the uploads it needs, stores
everything as a durable Business Profile, and turns it into context every
agent receives. "Learning" here is context engineering, not weight training:
answers → profile + memories → injected into briefs and chat. After intake,
an analyst workflow reviews the answers and writes what it learned to memory.

## 1. Data: `business_profile` table + `intake` report kind

`BusinessProfile` model in `models.py` — key/value/updated_at, exactly like
`FounderProfile`. New report kind `intake` (add to frontend `KIND_META` +
`types.ts` union).

## 2. `backend/app/venture/intake.py` — the interview as data

`INTAKE_QUESTIONS: list[dict]`, each
`{key, section, question, type: "short"|"long"|"number"|"choice", choices?,
required: bool, why: str}`. `key` is the `business_profile` key. Sections
and questions (keep this exact set; wording may be polished):

**Identity** — `name` (short, req: "What is the business called?");
`description_own_words` (long, req: "Explain your business in your own
words — what you sell, to whom, and how it makes money. Write like you're
telling a friend."); `founded` (short: "When did it start, and what stage is
it at?").

**Situation** — `situation_own_words` (long, req: "Describe the current
situation in your own words — what's going well, what's stuck, what
happened recently that matters."); `decision_pending` (long: "What decisions
are you facing right now?"); `biggest_worries` (long, req).

**Customers** — `customers_who` (long, req: "Who buys from you? Describe
your 2-3 main customer types."); `why_customers_buy` (long); `customer_count`
(short: "Roughly how many paying customers?").

**Money** — `revenue_monthly` (short, req: "Monthly revenue, roughly —
a range is fine."); `pricing_summary` (long, req: "What do you charge, and
how is it structured?"); `costs_summary` (long: "Your main costs, roughly.");
`margins_estimate` (short).

**Operations** — `team` (long: "Who works in the business and on what?");
`tools_systems` (long: "What software/tools run the business?");
`process_pain` (long: "Which repeated tasks eat the most time?").

**Growth** — `sales_channels` (long, req: "How do customers find you and
how do you close them?"); `marketing_summary` (long); `cac_knowledge`
(short: "Do you know your customer acquisition cost? If yes, what is it?").

**Market** — `competitors` (long); `differentiation` (long: "Why do
customers pick you over the alternatives?").

**Direction** — `goals_12mo` (long, req); `constraints` (long: "Hard
constraints: budget, time, people, regulations."); `avoid` (long: "Anything
you've decided NOT to do?").

Validation helpers mirror `founder.py`: `BUSINESS_KEYS` derived from the
questions, unknown-key rejection, per-type value caps (long 4000, others
1500). Also:

- `business_context(engine) -> str` — filled answers rendered as a
  `BUSINESS PROFILE (…)` block, `""` when empty (same contract as
  `founder_context`).
- `UPLOAD_MANIFEST: list[dict]` —
  `{key, label, accepts, purpose}` for: `transactions_csv`, `customers_csv`,
  `invoices_csv` (accepts `.csv`, purpose "loaded into the live database via
  the V6 importer — use the templates in docs/templates/"), and
  `context_docs` (accepts `.txt,.md`, purpose "narrative material — plans,
  notes, pitch text — stored as intake documents for the analyst review").

## 3. Context injection (the "OS knows the business" part)

- `workflows._brief` additionally appends `business_context(engine)` (after
  founder, before memories). No-op when the profile is empty.
- `AgentService.ask_ceo`: when `business_context(engine)` is non-empty,
  prepend to the user message:
  `"BUSINESS CONTEXT (the real company this chat is about):\n{context}\n\nREQUEST: {message}"`.
  Byte-identical behavior when the profile is empty. `ask_ceo` gains an
  `engine` made from settings at service construction (it already has
  `self.engine`). Keep the wrapped message out of the stored `history`
  duplication trap: append the ORIGINAL message to history, not the wrapped
  one.
- Operations agents' static "Lumina Labs" prompt context is explicitly OUT
  of scope (needs a prompt refactor — noted for V8).

## 4. Analyst review workflow: `intake_review`

Add to `VENTURE_WORKFLOWS` (label "Business intake review"). Runs after the
interview: **in parallel**, `venture_cfo`, `venture_cmo`, `risk` each get a
brief (`TOPIC: {business name or 'our business'}`) containing the FULL
business profile plus the list/excerpts of `intake` reports, instructed to
return: "What I learned / Assumptions to validate (numbered) / Red flags".
Deterministic code then saves:

- `Report(kind='intake', agent='coo', title=f"Business intake review: {name}")`
  with the three sections, and
- three memories: cfo output → `financial_assumption`, cmo →
  `customer_research`, risk → `risk` (each truncated, `related_idea` =
  business name, content ends with the report ref).

The workflow's `topic` argument is ignored in favor of the stored business
name when present (document this in the registry description). Demo mode
works unchanged — all three agents already have canned handlers.

## 5. API (in `main.py`, venture section)

- `GET /api/intake/questions` → `{sections: [...], questions: INTAKE_QUESTIONS,
  uploads: UPLOAD_MANIFEST}`.
- `GET /api/business` / `PUT /api/business` (body `{"values": {...}}`) —
  founder-endpoint pattern, 400 on unknown keys.
- `POST /api/intake/upload` — multipart `file` + form field `kind` (a
  manifest key). Enforce: extension per manifest, size ≤ 2 MB, sanitized
  filename. `.txt`/`.md` → `save_report(kind='intake', agent='human',
  title=f"Intake document: {filename}", content=text)`. `.csv` → write to
  `<data dir>/imports/<kind>.csv` and respond
  `{stored: true, next: "run scripts/import_real.py --source <dir> --check"}`
  — do NOT auto-import (a partial upload set would fail V6 validation;
  the response tells the human what to do). 400 on violations.

## 6. Frontend — `frontend/app/onboarding/page.tsx` + sidebar entry

Sidebar: `{ href: "/onboarding", label: "Business Setup", icon: ClipboardList }`.
A sectioned wizard driven ENTIRELY by `GET /api/intake/questions` (no
hardcoded question text in the frontend):

- Progress header (sections completed / required questions answered).
- One section at a time; inputs by type (`short`→input, `long`→textarea
  6-10 rows, `number`→numeric input, `choice`→select); the `why` text as a
  muted helper line; required markers.
- **Autosave**: PUT the section's non-empty values on section change and on
  a Save button; inline saved/error notice.
- Upload step from the manifest: file input per entry, purpose text, POST
  on select, show stored/next-step response inline.
- Finish step: shows completeness, then a "Have the team study the
  business" button → `POST /api/venture/intake_review` (topic: business
  name) → poll `/api/reports?kind=intake` (venture-page pattern) → link the
  review report; note that agents now use this context everywhere.
- Prefill from `GET /api/business` on load; empty states throughout.

## 7. Tests — `backend/tests/test_intake.py`

- Question integrity: keys unique and == `BUSINESS_KEYS`; both own-words
  questions present and `required`; every question has section/why/type in
  the allowed set.
- Profile roundtrip + unknown key 400 (API) + value caps.
- `business_context` empty→"", filled→contains name and own-words text.
- Chat injection: FakeClient-scripted `ask_ceo` — with profile set, the CEO's
  received message contains "BUSINESS CONTEXT"; history stores the original
  message; with empty profile, message passes through unchanged.
- Upload endpoint: txt→intake report row; csv→file lands in imports dir +
  response next-step; bad extension/oversize/unknown kind → 400.
- `intake_review` workflow (FakeClient, 3 markers): report with the three
  sections + the three memory rows with correct categories.
- Existing marker-safety and workflow tests stay green.

## Constraints

`AGENTS.md` hard rules. Files touched: `models.py` (one model, append),
`venture/intake.py` (new), `venture/workflows.py` (`_brief` + one workflow +
registry entry), `agents/service.py` (`ask_ceo` wrap only),
`api/venture.py` (profile helpers if not placed in intake.py), `main.py`
(venture section), `frontend/app/onboarding/page.tsx` (new),
`sidebar.tsx`/`types.ts`/reports `KIND_META` (append), tests. Nothing else.
No new dependencies (multipart uses FastAPI's built-ins; `python-multipart`
is already a FastAPI extra — if it is genuinely missing from
requirements.txt, adding it is the ONE permitted dependency, noted in the
commit body).

## Acceptance checklist

- [ ] Full pytest green; `npm run build` green.
- [ ] DEMO_MODE manual: complete the wizard with a fictional business,
      upload a .md note, run the review → intake report + 3 memories exist;
      a chat question shows business-aware context; venture workflows'
      briefs include the business block.
- [ ] Empty-profile behavior byte-identical to today (chat regression test).
