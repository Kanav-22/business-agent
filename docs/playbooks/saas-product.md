# Playbook: SaaS Product

Recurring-revenue software solving one expensive problem for a defined segment.
Slowest to first revenue in this library; strongest compounding after.

## Best niche examples
- Vertical ops tools (clinic scheduling, gym member management, freight quoting).
- Workflow glue for a specific stack ("Shopify + Tally reconciliation").
- Compliance/reporting automation for one regulation in one industry.
- Analytics for a niche the big BI tools ignore.

## Ideal customer profile
Teams of 2–50 in one vertical with a recurring, quantifiable pain (hours or money
lost weekly), a budget line for software, and a person who feels the pain
personally (they become your champion). B2B beats B2C for a first SaaS: fewer
customers needed, higher willingness to pay.

## MVP
The ONE workflow that delivers the promise — not the platform. One integration,
one happy path, manual onboarding (you set up every account yourself on a call).
4 weeks of build max; if it needs more, cut scope. A demo-able prototype + 5
design-partner commitments beats a finished product with zero users.

## Pricing model
Three tiers (good/better/best), priced on value metric that scales with usage
(seats, locations, volume) — e.g. $49/$149/$399 or ₹2k/₹6k/₹15k per month. Annual
= 2 months free. Charge from day one; free pilots time-boxed to 14 days. Design
partners: 50% off for 6 months in exchange for weekly feedback, never free forever.

## Sales channels
Founder-led sales for the first 50 customers: direct outreach to the ICP, demos on
calls, communities where the vertical gathers. Self-serve signup comes later —
before product-market fit it just hides why people don't buy.

## Marketing channels
SEO on the vertical's problem phrases (compounds by month 6+), comparison pages,
one channel of founder content (LinkedIn or the vertical's forum), integration
marketplace listings (Shopify/Slack app stores are distribution).

## Tech stack
Boring and fast: Next.js + Postgres + a managed host (Vercel/Railway), Stripe or
Razorpay for billing, Clerk/Auth.js for auth, one queue (Inngest/celery) for jobs.
Buy auth/billing/email — build only the differentiator.

## First 10 customers strategy
20 discovery calls in the niche BEFORE building → recruit 5 design partners from
them (50% off, weekly call) → build the MVP against their live data → convert
design partners to paid at month 2 → their logos + one case study recruit the next
5 via outreach.

## 30-day launch plan
(Assumes discovery already validated the problem.)
- **Week 1:** cut scope to one workflow; set up stack + billing; static landing
  page with a real waitlist.
- **Week 2–3:** build the workflow; weekly demo to design partners; fix what they
  trip on, ignore what they merely mention.
- **Week 4:** onboard all 5 partners hands-on; instrument activation + weekly-use
  events; first case-study draft; open 10 more outreach conversations.

## Common mistakes
Building for 6 months before the first user; free pilots with no end date;
"platform" thinking (multi-integration, settings pages) pre-PMF; pricing too low to
fund support; measuring signups instead of weekly active usage; ignoring churn
because MRR still grows.

## Risks
Platform dependency if built on one API (have a policy-change plan); a funded
competitor outspending you (win on niche depth); long sales cycles draining runway
(keep a services side-income until MRR covers costs); churn from weak onboarding
(do it manually far longer than feels scalable).

## KPIs
Weekly active accounts / paying accounts (the PMF signal), MRR + net revenue
retention, churn <3%/mo, CAC payback <6 months, activation rate (signup→first
value), demo→close rate.

## Scaling path
Founder-led sales → repeatable outbound playbook + first sales hire at ~$20k MRR →
self-serve tier for the low end → expand the value metric (more seats/locations) →
adjacent workflow #2 only after #1 retains >90%.
