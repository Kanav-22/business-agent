# Playbook: Data Analytics Agency

Turn companies' messy data into decisions: dashboards, reporting automation,
and analysis for businesses that have data but no data team.

## Best niche examples
- D2C/ecommerce: unified marketing + sales + inventory dashboards.
- Clinics/hospitals: patient-flow and revenue-cycle reporting.
- SaaS startups: metrics stacks (MRR, churn, cohort) investors ask for.
- Manufacturers/distributors: sales, margin, and stock analytics from ERP dumps.
- Franchises: per-location performance league tables.

## Ideal customer profile
Companies ₹5Cr–100Cr / $1M–20M revenue with data scattered across 3+ systems
(POS, ads, bank, ERP, spreadsheets), decisions made on gut feel, no analyst on
payroll, and a monthly reporting ritual that takes someone days. The buyer is the
founder/CFO who suspects money is leaking but can't see where.

## MVP
One fixed-scope "insight sprint": connect 2–3 sources, deliver one dashboard +
one written findings memo in 2 weeks for a fixed price. The memo (3 concrete
leaks found, with amounts) is what sells the retainer.

## Pricing model
Sprint ₹40–80k / $500–2,000 fixed → monthly retainer ₹15–50k / $300–1,500 for
maintained dashboards + a monthly insights memo + ad-hoc questions. Never bill
hourly. Price the retainer against the analyst salary they're not paying
(₹8–15L/year).

## Sales channels
Founder-led outreach to a named ICP list; accountants/CA firms as referral
partners (they see the messy books first); communities where the vertical's
founders gather; one anchor case study per vertical.

## Marketing channels
Teardown content: "we analyzed 20 D2C brands; the average leaks 8% of margin in
these 3 places"; LinkedIn posts with anonymized before/after dashboards; a free
"data health check" (30-minute call + checklist) as the lead magnet.

## Tech stack
Metabase/Looker Studio/Power BI (client-facing), a lightweight warehouse
(BigQuery/Postgres) when sources exceed 3, Fivetran/Airbyte or plain Python for
pipelines, dbt for transforms once retainers stack up, this AI Business OS
pattern (SQL agents + validated reports) for internal drafting. Standardize one
stack — every client on the same tooling is the scaling secret.

## First 10 customers strategy
Pick one vertical → free data health checks for 10 companies from warm/community
paths → each check ends with "we found these 3 questions your data can answer;
the sprint answers them" → close 3–5 sprints → 80% of good sprints convert to
retainers if the memo names money ("₹3.2L/month lost to channel X").

## 30-day launch plan
- **Week 1:** choose vertical; define the sprint package + template dashboard for
  that vertical; list 50 targets; 10 health-check invitations.
- **Week 2:** run 5 health checks; send 5 sprint proposals within 24 h; close 2.
- **Week 3:** deliver sprint #1 (dashboard + memo); weekly written update;
  continue outreach at 10/week.
- **Week 4:** sprint #1 memo lands with named leaks → retainer conversation;
  anonymize into case study #1; raise sprint price 20% for the next cohort.

## Common mistakes
Selling "dashboards" instead of found money (nobody budgets for charts);
unbounded scope ("just clean up our data"); custom stacks per client; skipping
the written memo (the dashboard alone doesn't renew retainers); underestimating
data-cleaning time (quote it — it's 60% of the work); dashboards without an
owner on the client side (they go stale and churn follows).

## Risks
Client data security (access via read-only credentials, a signed DPA, per-client
isolation — one breach ends the agency); source-system API changes breaking
pipelines (monitoring + a maintenance clause in the retainer); insight
liability (label assumptions; the memo informs, the client decides); key-person
dependency (SOPs and the standardized stack from client #1).

## KPIs
Health-check→sprint close (≥30%), sprint→retainer conversion (≥60%), MRR,
retainer churn (<3%/mo), delivery hours per sprint (falling), leaks found per
memo (the sales asset), pipeline uptime.

## Scaling path
One vertical's template → junior analyst per 6–8 retainers → the vertical's
template dashboard becomes semi-productized (fixed connectors, 2-day setup) →
either scale the agency by vertical or turn the best template into an analytics
SaaS for that vertical (`saas-product.md`) with retainer clients as design
partners.
