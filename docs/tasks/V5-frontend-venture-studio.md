# Task V5 — Venture Studio frontend + README

**Branch:** `codex/v5-frontend` (from the integration branch after V3 is
merged — the page calls the V3 endpoints).
**Read first:** `AGENTS.md`, `frontend/app/reports/page.tsx` (THE pattern:
`getJson`, poll, `JobButton`, `KIND_META`, markdown rendering),
`frontend/components/sidebar.tsx`, `frontend/lib/types.ts`.

**Explicitly NOT in this task** (architect deliverables): `OS_TEMPLATE.md`,
`docs/SYSTEMS_REPORT.md`.

## Goal

One new dashboard page — **Venture Studio** — exposing the venture layer:
run workflows, browse scored ideas, test the router, edit the founder profile,
browse memories and playbooks. Keep the existing dark "mission control" look;
reuse existing components (`Markdown`, card/badge styles from the reports
page) instead of inventing new ones.

## 1. API contract (already live on the backend)

- `GET /api/venture/workflows` → `[{name, label, description}]`
- `POST /api/venture/{name}` body `{"topic": string}` → 202 `{started, workflow}`;
  409 while running; 400 empty topic. Results land in `/api/reports?kind=<name>`
  (kinds: `debate`, `failure_sim`, `interviews`, `idea_score`).
- `GET /api/ideas` → `[{id, title, total_score, verdict, created_at, excerpt}]`
  (`verdict` ∈ `go|no_go|test_first`); `GET /api/ideas/{id}` adds
  `description, scores {cat: {score, rationale}}, best_version, worst_risk,
  validation_test, next_actions`.
- `POST /api/route` body `{"message": string}` → `{category, primary_agent,
  supporting_agents[], workflow[], risk_level, reason, required_inputs[],
  expected_output, matched_categories[], founder_fit_note?, warnings[]}`.
- `GET /api/founder` → `{skills, weaknesses, working_style, risk_tolerance,
  budget_range, long_term_goals, current_assets, coding_ability,
  business_interests, communication_style, decision_flaws, how_to_challenge,
  how_to_focus, distracting_ideas, avoid, double_down}` (all strings, may be
  empty); `PUT /api/founder` body `{"values": {<subset of those keys>}}`.
- `GET /api/memories?category=&status=active` →
  `[{id, category, title, content, source_agent, related_idea, status, created_at}]`;
  `POST /api/memories/{id}/archive`.
- `GET /api/playbooks` → `[{slug, title}]`; `GET /api/playbooks/{slug}` →
  `{slug, content}` (markdown).
- `GET /api/evals` → eval rows (show a simple table if any; empty state text
  pointing to `backend/evals/README.md`).

## 2. Files

### `frontend/lib/types.ts` (append only)

Extend `ReportSummary["kind"]` union with
`"debate" | "failure_sim" | "interviews" | "idea_score" | "eval"`. Add
interfaces: `VentureWorkflow`, `IdeaSummary`, `IdeaDetail`, `RouteDecision`,
`FounderProfile` (Record of the 16 keys), `Memory`, `PlaybookSummary`,
`Playbook`, `EvalRow`.

### `frontend/app/reports/page.tsx` (append only)

Add the five kinds to `KIND_META` with distinct badge styles, labels:
`Board debate`, `Failure sim`, `Interviews`, `Idea score`, `Eval`.

### `frontend/components/sidebar.tsx` (append only)

`NAV` entry `{ href: "/venture", label: "Venture Studio", icon: Rocket }`
(lucide-react `Rocket`). If a `UPCOMING` list mentions any of these features,
remove only entries this page now delivers (allowed exception to
append-only, keep the rest).

### `frontend/app/venture/page.tsx` (new, `"use client"`)

Tabbed or stacked sections in this order:

1. **Run a workflow** — one text input ("business idea or decision topic") +
   four buttons (from `GET /api/venture/workflows`). On click: POST; disable
   the button while awaiting; then poll `/api/reports?kind=<name>&limit=1`
   every 3s (max ~2 min) until a report newer than the click timestamp
   appears; show a link/inline view of it (reuse the reports detail pattern
   or link to `/reports`). Surface 409 ("already running") and 400 as inline
   errors. Show a hint that with `DEMO_MODE=1` results are canned but real.
2. **Idea scoreboard** — table of `/api/ideas`: title, total (e.g. `5.5/10`),
   verdict badge (`go` green, `test_first` amber, `no_go` red), date;
   clicking a row expands the detail (scores table with rationale, best
   version, worst risk, validation test, next actions).
3. **Router tester** — input + button → render the RouteDecision: primary
   agent, supporting agents (chips), workflow sequence (→ separated),
   risk-level badge (low/medium/high), reason, required inputs,
   founder-fit note and warnings (amber callouts).
4. **Founder profile** — form of 16 labeled textareas (labels from the key
   names, humanized; short helper line under each from
   `docs/FOUNDER_CLONE_TEMPLATE.md` one-liners); single Save button → PUT
   with all non-empty values; success/failure toast-like inline note.
5. **Memories** — category filter dropdown (the 16 categories + All) +
   list of cards (title, category chip, content, source agent, date) with an
   Archive button per card.
6. **Playbooks** — list from `/api/playbooks`; clicking loads
   `/api/playbooks/{slug}` and renders with the existing `Markdown`
   component in a scrollable panel.

Empty states for every section (no ideas yet, profile unset, etc.) — one
helpful sentence each, no blank panels.

### `README.md` (append a section, do not modify existing text)

`## Venture layer (Phase V)` — 10-15 lines: what it is (the 12 systems, one
sentence), the Venture Studio page, the four workflow curls, the router curl,
`SURVIVAL_MODE` / `VENTURE_IN_CHAT` env vars appended to the existing env
table (add rows only), eval runner one-liner, pointer to `docs/` and
`docs/SYSTEMS_REPORT.md`.

## 3. Gates

- `cd frontend && npm run build` passes (this is the type-check gate).
- `cd backend && python3 -m pytest` untouched-green (you should not need to
  touch backend code at all; if you believe you do, stop and leave a note in
  the commit body instead).
- Manual smoke with `DEMO_MODE=1` backend + `npm run dev`: run all four
  workflows from the page, see reports; save a founder profile; route the
  doctor example (expect HIGH risk badge + risk officer chip); archive a
  memory; open a playbook.

## Acceptance checklist

- [ ] Files touched: `frontend/app/venture/page.tsx` (new),
      `frontend/lib/types.ts`, `frontend/app/reports/page.tsx` (KIND_META),
      `frontend/components/sidebar.tsx`, `README.md` — nothing else.
- [ ] No new npm dependencies.
- [ ] Existing pages pixel-identical (no shared-component edits).
