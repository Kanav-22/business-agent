# Playbook: Micro-SaaS

A tiny software product solving one narrow problem, run by one person, profitable
at small scale. Optimizes for founder freedom, not venture scale.

## Best niche examples
- Single-feature tools riding a platform: Shopify shipping-label tweaks, Notion
  invoice generators, YouTube chapter tools.
- One report/export a profession needs monthly (GST summaries, timesheet exports).
- A painful integration between two specific tools.
- Calculators/generators with proven search volume.

## Ideal customer profile
Prosumers and small businesses already inside a platform ecosystem, self-serve
buyers who decide alone in one session, price-tolerant to $5–50/month because the
tool clearly saves an hour or unlocks money.

## MVP
One feature, one page, one price. Build in 1–2 weeks. No settings, no teams, no
API. The landing page IS the spec: if the headline can't promise the outcome in one
sentence, the product is too broad.

## Pricing model
$9–29/month single plan (or one plan + a 2× "pro" tier), or lifetime deal
$49–99 for the first 100 customers to fund the runway. Monthly beats lifetime
long-term; lifetime beats nothing at launch.

## Sales channels
Self-serve only: platform app stores/marketplaces (Shopify, Chrome Web Store,
Notion gallery, Figma community), which bring the traffic for you. This channel
choice is 80% of the business decision.

## Marketing channels
SEO on the exact problem phrase ("export notion database to invoice"), a free tier
or free tool as top-of-funnel, launch posts (Product Hunt, relevant subreddits, the
platform's community), comparison/alternative pages.

## Tech stack
The smallest thing that ships: Next.js or plain HTML + one serverless backend,
Stripe Payment Links (skip billing code), Supabase/SQLite, the platform's SDK.
Hosting bill target: <$20/month.

## First 10 customers strategy
Find 10 people complaining about the exact problem (subreddit/forum/app-store
reviews of a clunky incumbent) → reply with a genuinely helpful answer + the tool →
offer founding-user lifetime pricing → ask each what almost stopped them from
paying, fix that, repeat.

## 30-day launch plan
- **Week 1:** validate search/marketplace demand (keyword volume, competitor
  reviews); build the core feature.
- **Week 2:** landing page + Stripe link; 10 manual outreach replies to complainers;
  soft-launch to them.
- **Week 3:** marketplace/app-store listing submitted (review takes days–weeks);
  fix onboarding friction from the first users.
- **Week 4:** public launch (Product Hunt / subreddit / platform community); publish
  the SEO page for the problem phrase; first 10 paying target.

## Common mistakes
Adding features instead of finding buyers; building off-platform where no traffic
flows; underpricing at $2/month (support costs more); chasing B2C virality instead
of search intent; quitting at month 2 when SEO hasn't compounded yet.

## Risks
Platform risk is existential here (one policy change kills the business — keep
the customer email list off-platform); the feature being absorbed by the platform
itself (pick problems too niche for their roadmap); solo-founder bus factor (write
a runbook once revenue is real).

## KPIs
Marketplace impressions → install rate, visitor → paid conversion (target 1–3%
self-serve), MRR, churn (<6%/mo acceptable at this price point), support tickets
per 100 customers (keep <5), hours/week to run it (target <10).

## Scaling path
More SEO pages → sister micro-tools sharing the audience (a portfolio, not a
platform) → raise price as reviews accumulate → either hold as passive income or
bundle the portfolio into one subscription.
