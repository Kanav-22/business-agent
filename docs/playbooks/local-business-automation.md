# Playbook: Local Business Automation

Automate the operations of brick-and-mortar businesses in your city — bookings,
reminders, reviews, reorders, payroll prep. Low competition, high trust
requirements, relationship-driven sales.

## Best niche examples
- Clinics/dentists/physios: bookings, reminders, no-show recovery.
- Salons/spas: slot filling, rebooking nudges, birthday campaigns.
- Restaurants: reservation + review funnels, WhatsApp ordering.
- Gyms/coaching centers: lead follow-up, fee reminders, attendance alerts.
- Kirana/pharmacy: reorder lists, supplier WhatsApp ordering.

## Ideal customer profile
Owner-operated local business, 3–30 staff, smartphone-first (WhatsApp is the
office), losing visible money to missed calls/no-shows/unfollowed leads, willing
to pay ₹5–15k/month if shown the leak in their own numbers. The owner buys on
trust and proof, not features.

## MVP
One automation for one business type, demonstrated live in their shop on their
phone: e.g. "missed-call → automatic WhatsApp with booking link → reminder day
before → review request after". Behind the scenes: n8n/Zapier + WhatsApp API.
No dashboard — owners want results in WhatsApp, not another app.

## Pricing model
Setup ₹5–15k + ₹5–15k/month per location. Anchor to one number from THEIR
business: "you had 62 missed calls last month; if 10 become bookings at ₹800,
that's ₹8,000 — this costs ₹6,000." Collect via auto-debit/UPI mandate — local
churn is often just payment friction.

## Sales channels
Walk-ins and phone calls (this is a face-to-face trade), one anchor client per
market who introduces you to their trade association/WhatsApp group, referrals
with a one-month-free incentive, local vendor partnerships (the POS dealer, the
accountant who serves 40 shops).

## Marketing channels
Hyper-local proof: a 60-second video of the anchor client saying "my no-shows
halved"; Google Business profile + local SEO ("clinic automation [city]");
WhatsApp status/broadcast to your growing owner network. Skip broad social ads —
the market is 200 shops, not 2 million.

## Tech stack
WhatsApp Business API (file day 1; 1–3 week approval), n8n/Zapier/Make, Google
Calendar/Sheets as the client-visible layer, UPI/Razorpay for mandates, a
missed-call number service. Everything must survive the owner's phone being the
only computer.

## First 10 customers strategy
Pick ONE business type in a 3-km radius → visit 30 as a customer first, note the
leaks → return with a one-page "your numbers" pitch for 15 → free 2-week pilot
for 3 (chosen for talkativeness, not size) → convert with the results sheet →
each pilot's owner introduces 2 peers (local trades all know each other).

## 30-day launch plan
- **Week 1:** choose niche + radius; file WhatsApp API; build the flow on your
  own number; visit 15 businesses.
- **Week 2:** 3 pilots live (manual fallback where the API is pending); daily
  check-ins; capture before/after numbers.
- **Week 3:** visit 15 more with pilot results in hand; convert pilot #1 to
  paid; get the first association-group introduction.
- **Week 4:** 5+ paying target; standardize onboarding to one visit + 2 hours;
  print simple one-page flyers (yes, print — this market reads paper).

## Common mistakes
Selling software instead of found money; too many business types at once (every
niche has different flows); building an app/dashboard nobody opens; skipping
auto-debit (chasing ₹6k payments kills you); underestimating handholding (the
first month is support-heavy — budget it); no local language in flows and
marketing.

## Risks
WhatsApp/Meta policy dependency (keep SMS/IVR fallbacks); owner churn on
cash-flow dips (annual prepay discount hedges); you as the only support line
(document + train a local VA by client #10); data privacy of customer lists
(simple consent + a one-page DPA builds trust and protects you).

## KPIs
Visits→pilot rate, pilot→paid (≥60%), MRR per location, churn (<4%/mo),
no-show/missed-call reduction per client (the selling number), support
hours per client per month (should fall below 2 by month 2), referral share of
new clients (target >50% by month 3).

## Scaling path
One niche × one area → same niche across the city via referrals/associations →
adjacent niche with 70% flow reuse → hire a local ops person per 15–20 clients →
package the niche playbook for other cities (license/franchise it, or productize
into the `ai-chatbot-product.md` / `micro-saas.md` motion).
