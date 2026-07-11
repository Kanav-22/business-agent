# Task V8 — Sellable frontend: 3D marketing site + product polish

**Branch:** `codex/v8-website` (from the integration branch AFTER V7 merges —
V7 adds frontend files that this task's restructure must include).
**Read first:** `AGENTS.md`, `frontend/app/**` (current pages),
`frontend/tailwind.config.ts`, `frontend/components/sidebar.tsx`.

## Goal

Turn the frontend into something a founder can demo and sell: a striking 3D
marketing landing page at `/`, and a consistent, branded, professional
product shell for the dashboard — without changing any dashboard
functionality. Honesty note: "sellable" here means the face of the product;
auth/billing/multi-tenant remain Phase 5.

## Allowed new dependencies (the ONE task where new deps are pre-approved)

`three`, `@react-three/fiber`, `@react-three/drei`. Nothing else (no UI kits,
no animation libraries — Tailwind + CSS + R3F only).

## 1. Route restructure (Next.js route groups)

```
frontend/app/
  (marketing)/page.tsx            ← NEW landing page at "/", NO sidebar
  (marketing)/layout.tsx          ← minimal layout (no sidebar, own footer)
  (app)/layout.tsx                ← the existing sidebar shell moves here
  (app)/overview/page.tsx         ← the current app/page.tsx moves here
  (app)/chat|activity|reports|approvals|venture|onboarding/…  ← moved as-is
```

- Page component INTERNALS must not change — `git diff --find-renames` should
  show moves, not rewrites (small import-path fixes allowed).
- Sidebar: "Overview" href becomes `/overview`; add a small brand block at
  the top (logo mark + product name) linking to `/overview`, and a muted
  "← Website" link to `/` at the bottom.
- `next.config.mjs`: permanent redirect nothing — old deep links all keep
  working; only "/" changes meaning.

## 2. Branding (`frontend/lib/brand.ts`)

```ts
export const BRAND = {
  name: process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "AI Business OS",
  tagline: "A boardroom of AI executives for your business.",
};
```

Landing page, sidebar, and `<title>` metadata read from this — one place to
rebrand. Add a simple geometric SVG logo mark (hexagonal node-cluster motif,
inline component, no image files) used in the sidebar and landing nav.

## 3. The landing page (`(marketing)/page.tsx`)

Dark, premium, calm. Design tokens: background `#0a0f1a` → `#101827`
gradients; text slate-100/slate-400; ONE accent `#a78bfa` (violet — the CEO
color already used in the app) with `#22d3ee` (cyan) as the secondary used
sparingly; generous whitespace; `tracking-tight` display headings
(Inter/system stack, no webfont downloads); max-w-6xl sections; subtle
1px `border-white/5` card borders; no drop-shadow soup.

Sections, in order:

1. **Hero with the 3D scene** (see §4). Left: headline
   "{BRAND.name}" + one-line pitch ("Nine AI executives. One command
   center. Your business." — copy may be refined but stays concrete, no
   hype clichés), two CTAs: primary "Open the dashboard" → `/overview`,
   secondary "See how it works" → anchor. Right (or background): the 3D
   canvas.
2. **The org chart strip** — the real agent roster rendered as styled chips
   grouped by team (pull the names/colors statically from a small constant
   mirroring `/api/agents` teams; do NOT fetch — the landing must render
   with the backend off).
3. **How it works** — three cards: Ask (chat + delegation tree), Decide
   (debate/score/simulate workflows), Operate (reports, approvals,
   memory). Each with a small inline SVG illustration, not screenshots.
4. **The 12 systems grid** — 12 compact cards (title + one line each),
   content from `docs/SYSTEMS_REPORT.md` §2 table, hover lift + accent
   border.
5. **Built to survive model downgrades** — the differentiator section:
   survival kit, deterministic verdicts, evals; one strong paragraph + three
   stat-style tiles (e.g. "159 tests", "18 eval scenarios", "4 debate-tested
   workflows").
6. **Run it your way** — three columns: Demo mode ($0), Free LLM (Gemini via
   proxy), Your data (CSV import) — each linking to the relevant doc on
   GitHub.
7. **Footer** — brand, GitHub link, "Built with the OS Template" link, no
   fake company/address/testimonials. NEVER invent customer logos, reviews,
   or metrics that don't exist.

## 4. The 3D hero scene (R3F, `frontend/components/three/hero-scene.tsx`)

Concept: **the boardroom as a constellation** — a central luminous node (the
CEO) orbited by 9 agent nodes (use the real roster colors), connected by
slowly pulsing curved lines (delegations). Behavior:

- Gentle idle rotation (~0.05 rad/s); nodes bob on offset sine phases;
  connection lines pulse opacity 0.15→0.4.
- Mouse parallax: scene tilts ±6° toward the cursor (lerped, no snap).
- On CTA hover: pulse ripples outward from the CEO node once.
- Materials: emissive spheres + additive-blend lines; soft bloom LOOK
  achieved with sprite glow textures or emissive intensity — do NOT add a
  postprocessing dependency.
- Stars/particles: max ~300 points, size-attenuated, barely moving.

Performance & accessibility budgets (hard requirements):
- Lazy-load the scene (`next/dynamic`, `ssr: false`); the hero renders
  headline+CTAs immediately with a static CSS radial-gradient placeholder.
- `prefers-reduced-motion: reduce` → render the static placeholder only.
- No WebGL (feature-detect) → static placeholder only.
- Canvas `frameloop="demand"`-style throttling or capped DPR (≤1.5); target
  <200KB gzip added JS for three+scene beyond the base page (verify with
  `npm run build` output; document the numbers in the commit body).
- Pause the render loop when the canvas is off-screen (IntersectionObserver).

## 5. Dashboard polish (restrained — do NOT redesign flows)

- Consistent page header component (title, subtitle, action slot) applied to
  all app pages — visual only, no logic changes.
- Unify card styles/spacing via small shared classes; fix any obvious
  spacing/alignment inconsistencies.
- `<title>`/metadata per page (`BRAND.name — Overview`, etc.), favicon
  (inline SVG logo), dark scrollbars.
- Loading skeletons where pages currently flash empty (Overview, Reports,
  Venture) — visual only.

## 6. Gates & tests

- `cd frontend && npm run build` green; list the landing route's JS size in
  the commit body.
- `cd backend && python3 -m pytest` untouched-green (no backend changes at
  all).
- Manual: with the backend OFF, `/` renders fully (3D or fallback) — the
  landing page must never depend on the API; with backend ON, every moved
  dashboard page works exactly as before (chat, workflows, approvals,
  onboarding).
- Reduced-motion emulation renders the static hero.

## Acceptance checklist

- [ ] Files: `(marketing)/*` new, `(app)/*` moves, `components/three/*` new,
      `lib/brand.ts` new, sidebar/layout/metadata edits, `package.json`
      (three deps) — nothing else; zero backend changes.
- [ ] No invented logos/testimonials/metrics; all numbers real (tests,
      scenarios, workflows).
- [ ] Landing works offline-from-backend, degrades without WebGL, respects
      reduced motion.
- [ ] Existing dashboard pages byte-equivalent in behavior (moves +
      header/skeleton polish only).
