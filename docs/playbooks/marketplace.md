# Playbook: Marketplace

Connect supply and demand and take a cut. The hardest model in this library —
you're building two businesses at once. Only choose it when you have unfair access
to one side.

## Best niche examples
- Booking niche professionals (physio at home, wedding photographers, tutors for
  one exam).
- Equipment rental within one city (cameras, tools, event gear).
- B2B surplus/liquidation within one industry.
- Curated talent marketplaces for one skill (Shopify developers, medical writers).

## Ideal customer profile
**Demand side:** buyers with an urgent, recurring need who can't easily find/vet
supply today. **Supply side:** fragmented providers (no dominant player owns
them) with idle capacity, hungry for demand. If supply is concentrated or
demand is one-off, the model leaks.

## MVP
A concierge marketplace: a form/WhatsApp number on one side, a spreadsheet and
phone calls behind it. YOU are the matching algorithm for the first 100
transactions. No two-sided platform build — software comes after liquidity.

## Pricing model
Take rate 10–25% of transaction value (who pays depends on who gets more value —
usually supply pays for demand). Alternatives when take rates leak: subscription
for supply-side leads, listing fees, or SaaS-enabled marketplace (tools +
transactions).

## Sales channels
Supply: direct recruitment (they want leads — this is the easy side; get 20–30
committed before demand launch). Demand: the niche's existing watering holes,
local SEO ("X near me"), partnerships with adjacent services.

## Marketing channels
Hyper-local/niche focus: one city or one vertical until liquidity. Supply-side
profiles double as SEO pages. Reviews are the trust engine — collect from
transaction #1. Paid ads only on the demand side, only after match rate >70%.

## Tech stack
Start: Tally/WhatsApp + Airtable + manual matching. After liquidity: Next.js +
Postgres, Stripe/Razorpay Connect-style split payments, Twilio/WhatsApp for
notifications. Build booking/matching only when manual coordination breaks
(~20+ transactions/week).

## First 10 customers strategy
(First 10 *transactions*.) Recruit 20 supply-siders personally with "free leads,
pay only on booking" → generate demand with 5 posts in local/niche groups +
₹3–5k of local ads → manually match, attend/monitor the first transactions,
fix every friction point → capture both-sides reviews.

## 30-day launch plan
- **Week 1:** pick ONE niche in ONE city; recruit 20 supply-siders by phone;
  define the standard offer (price bands, what's included) so buyers compare
  apples to apples.
- **Week 2:** demand landing page + WhatsApp intake; first posts/ads; first 3
  manual matches.
- **Week 3:** 10+ transactions; measure match rate and time-to-match; collect
  reviews; raise take rate from 0% (launch subsidy) to target on new matches.
- **Week 4:** double down on whichever side is the constraint (it's usually
  demand); document the matching heuristics — that's the future product spec.

## Common mistakes
Building the platform before liquidity; going multi-city/multi-category early;
subsidizing both sides indefinitely; ignoring disintermediation (parties settle
off-platform — fight it with payments protection, insurance, reviews, not with
policing); measuring signups instead of completed transactions; letting bad
supply poison early demand (curate ruthlessly).

## Risks
Chicken-and-egg failure (mitigate: single-player value for supply — free tools/
profile even without matches); disintermediation; quality incidents on
transactions you facilitated (insurance, vetting, clear liability terms);
regulatory exposure depending on category (transport, healthcare, finance all
have rules); take-rate compression from competitors.

## KPIs
Liquidity: match rate (>70%), time-to-match, fill rate per request. Health: GMV,
net take rate, repeat transaction rate per side, supply utilization,
disintermediation estimate (survey buyers), NPS both sides.

## Scaling path
One niche/city liquid → replicate city-by-city (playbook + local supply lead) →
automate matching from documented heuristics → payments + guarantees on-platform
(the anti-disintermediation moat) → SaaS tools for supply side → category
expansion only when the core repeats >30%.
