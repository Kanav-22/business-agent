# Review — Task V8 (`codex/v8-website` @ `17bf401`)

Reviewer: Claude (architect). Verified on a test merge against integration
tip `d7130e9`.

## Verification performed

- Scope: frontend-only + `package.json`/lock (exactly the three pre-approved
  dependencies: three, @react-three/fiber, @react-three/drei). Rename
  detection confirms moves-not-rewrites (R079-R100 similarity on all moved
  pages; residual diffs are import paths + page-header adoption).
- Backend suite untouched: **168/168**.
- Production build green. Landing route **5.51 kB / 102 kB first-load** —
  matches the implementer's report; three.js is fully out of the initial
  chunk (dynamic import, ssr:false, static underlay while loading).
- Lazy 3D payload measured: 130 kB (three core) + 38 kB (fiber+scene)
  ≈ **168-172 kB gzip — under the 200 kB budget**, corroborating the
  reported 172.16 kB. (An initial 229 kB reading on my side wrongly summed
  the pre-existing recharts chunk; noted for honesty.)
- Backend-off render smoke on the built site: all 8 routes (/, /overview,
  /chat, /activity, /reports, /approvals, /venture, /onboarding) returned
  200 as static prerenders; landing contains the brand + pitch with no API
  dependency.
- Gating code inspected: `prefers-reduced-motion` (live media-query
  listener), WebGL detect with `failIfMajorPerformanceCaveat`,
  IntersectionObserver + `visibilitychange` render-loop pause, DPR capped
  at 1.5, `frameloop` switching. Static fallback always renders as the
  underlay — no blank-canvas failure mode.
- Truthfulness audit: stat tiles are real and CURRENT (168 backend tests,
  18 eval scenarios, 5 deterministic workflows; the spec's stale example
  "159" was corrected to reality — exactly the right instinct). The
  21-agent roster mirrors the product exactly, colors included. No
  fabricated logos/testimonials/metrics. Only external link is the user's
  own GitHub repo, with doc links pinned to a commit SHA so they cannot
  rot. No external fonts/CDNs/analytics.

## Findings

BLOCKING: none.

IMPORTANT: none.

OPTIONAL:
1. Doc links pinned to `d7130e9` will age as the branch advances —
   intentional (never-breaking) and fine; revisit when docs stabilize on a
   default branch.
2. Per-page `layout.tsx` files exist only to carry metadata titles; a
   shared helper could slim them. Cosmetic.

ARCHITECTURAL VERDICT: Conforms. Route groups split marketing from app
cleanly; brand constant with env override; the hero shell/scene/fallback
separation keeps the graceful-degradation logic testable and out of the
page. The `data-hero-support` attribute is a nice testing hook.

TESTING VERDICT: Meets the gates (build + untouched backend + documented
manual matrix); runtime claims independently reproduced here, including the
bundle-size claim.

ACCEPT / REQUEST CHANGES: **ACCEPT** — merged into
`claude/agent-operating-system-66e55h`. Codex: 6 for 6, zero blocking
findings.
