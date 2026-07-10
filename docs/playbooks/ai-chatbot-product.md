# Playbook: AI Chatbot Product

Sell a packaged chatbot that does ONE job for ONE business type — support
deflection, lead capture, booking, internal knowledge. "A chatbot" is not a
product; "cuts repeat support questions 60% for Shopify stores" is.

## Best niche examples
- Support deflection for ecommerce (order status, returns, sizing).
- Lead qualification + booking for local services (clinics, salons, agencies).
- Internal policy/knowledge bots for HR or IT teams.
- Course/community Q&A bots for creators with large content libraries.

## Ideal customer profile
Businesses with high repeat-question volume (≥20/day), existing content to ground
answers in (FAQs, docs, catalogs), and a measurable cost of the status quo
(support headcount hours, missed leads after hours). The buyer owns that cost.

## MVP
One channel (web widget OR WhatsApp), one job, grounded strictly in the client's
content with citations, human-handoff built in from day one, and an
unanswered-questions log. Ship in 1–2 weeks using existing frameworks — the moat
is workflow fit and data quality, not the model.

## Pricing model
Setup ₹10–30k/$150–400 + ₹5–20k/$75–250 per month, tiered by conversation
volume. Price against the hours saved or leads captured, never per-token. Pilot:
14 days, success metric agreed in writing upfront ("≥50% of repeat questions
answered without a human").

## Sales channels
Direct outreach to the niche with a demo bot trained on THE PROSPECT'S OWN
public content (the demo is the pitch — 10 minutes of setup, devastatingly
effective); agency partnerships (web agencies resell it); platform marketplaces
(Shopify App Store, WhatsApp solution partners).

## Marketing channels
Before/after case studies with deflection numbers; short screen-recordings of the
bot answering real questions; SEO on "niche + chatbot/automation"; free
"bot-readiness audit" of a prospect's FAQ as lead magnet.

## Tech stack
Claude API (use the newest available model tier for answer quality) + RAG over
the client's content (managed vector store or pgvector), a chat-widget framework
or WhatsApp Business API, human-handoff to email/WhatsApp/Slack, an admin view
showing conversations + unanswered log. Guardrails: grounded-only answers,
refusal on out-of-scope, PII scrubbing in logs.

## First 10 customers strategy
Pick one niche → build demo bots on 10 prospects' public FAQs → send each a
2-minute video of THEIR bot answering THEIR customers' questions → 14-day pilot
with the agreed metric → convert at full price; unanswered-questions reports
create the expansion conversation ("your bot got 40 questions about X you have
no content for").

## 30-day launch plan
- **Week 1:** niche + job chosen; build the reusable pipeline (ingest → RAG →
  widget); demo bot for your own site.
- **Week 2:** 10 prospect demo bots + videos sent; 5 pilot conversations; sign 3
  pilots with written success metrics.
- **Week 3:** pilots live; daily log review; tune retrieval + handoff; weekly
  metric email to each pilot.
- **Week 4:** pilots hit/miss metrics → convert winners to paid; case study #1;
  systematize onboarding to <1 day per client.

## Common mistakes
Selling "AI" instead of a metric; letting the bot answer ungrounded (one
hallucinated refund policy destroys the account); skipping human handoff;
unlimited-usage pricing that inverts your margin at scale; custom-building per
client instead of one pipeline with per-client content; ignoring the unanswered
log (it's both QA and upsell).

## Risks
Hallucination liability — mitigate with grounded-only answers, citations, refusal
behavior, and a written disclaimer + review period in the contract; prompt
injection / data leakage (isolate client data per tenant, scrub PII); model API
price/policy changes (abstract the provider); platform rules on WhatsApp/Meta;
client content going stale (scheduled re-ingestion + change alerts).

## KPIs
Deflection rate (answered-without-human), answer groundedness (spot-check
score), handoff rate, unanswered-question count trend, conversations/month per
client, MRR, churn (<4%/mo), onboarding hours per client (target <8).

## Scaling path
One niche pipeline → templatize per-niche content packs → self-serve onboarding
for the low tier → marketplace listings → expand the JOB (booking → payments →
reorders) inside the same clients rather than expanding niches early. The agency
version of this playbook (`ai-automation-agency.md`) is the manual-first sibling;
this one productizes it.
