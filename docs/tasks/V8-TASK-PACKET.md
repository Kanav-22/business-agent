# TASK PACKET

TASK ID: V8

TITLE: Sellable frontend — 3D marketing landing page + branded product shell

BASE BRANCH: claude/agent-operating-system-66e55h (AFTER V7 is merged)

BASE COMMIT SHA: tip of BASE BRANCH at task start (see chat handoff)

OBJECTIVE: Give the OS a face worth selling: a premium dark 3D landing page
at "/" (the agent boardroom as an animated constellation) and a branded,
consistent dashboard shell — with zero functional changes to the product.

ARCHITECTURAL CONTEXT: Next.js 14 app router; route groups split
`(marketing)` from `(app)`; React Three Fiber for the hero scene with hard
performance/accessibility budgets and static fallbacks. Normative spec:
`docs/tasks/V8-marketing-frontend.md`.

FILES OR AREAS IN SCOPE: `frontend/**` only — route-group restructure
(moves, not rewrites), `(marketing)` pages, `components/three/*`,
`lib/brand.ts`, sidebar/layout/metadata polish, `package.json` (+three,
+@react-three/fiber, +@react-three/drei — pre-approved for this task only).

FILES OR AREAS OUT OF SCOPE: the entire backend; docs; page component
logic/flows; no other dependencies (no UI kits, no postprocessing, no
animation libs).

FUNCTIONAL REQUIREMENTS: per spec — landing sections 1-7 with real content
only (no fabricated logos/testimonials/metrics); 3D scene behavior (idle
rotation, parallax, pulse), lazy-load + reduced-motion + no-WebGL static
fallbacks, off-screen pause, DPR cap; brand constant + env override; moved
dashboard routes with "Overview" at /overview; page headers, metadata,
favicon, skeletons.

ACCEPTANCE CRITERIA: spec checklist; `npm run build` green with the
landing-route JS size reported in the commit body; backend pytest
untouched-green; landing renders fully with the backend off.

REQUIRED TESTS: build gate + manual matrix in spec §6 (document results in
the commit body — backend-off render, reduced-motion, moved-page smoke).

SECURITY AND EDGE CASES: no external requests from the landing (fonts,
CDNs, analytics — none); all assets inline/local; feature-detect WebGL;
never block paint on the 3D bundle.

CONSTRAINTS: AGENTS.md hard rules; copy tone concrete and hype-free (the
Sales survival guide's banned-cliché list applies to our own site).

DEPENDENCIES: V7 merged (its onboarding page must be inside the `(app)`
group and styled by the same shell).

KNOWN RISKS: route-group moves breaking relative imports (fix imports only);
three.js bundle bloat (budget: <200KB gzip added on the landing route — cut
drei helpers if needed); WebGL blank-screen on low-end devices (fallback is
mandatory, test it).

EXPECTED DELIVERABLE: branch `codex/v8-website` pushed, gates green,
ambiguity decisions + bundle numbers in the commit body.
