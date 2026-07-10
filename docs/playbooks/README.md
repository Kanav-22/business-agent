# Business Playbook Library

Reusable launch templates for the business types the venture layer supports. Each
playbook has the same 13 sections so agents (and you) can diff business models
side by side: niches, ideal customer profile, MVP, pricing model, sales channels,
marketing channels, tech stack, first-10-customers strategy, 30-day launch plan,
common mistakes, risks, KPIs, scaling path.

They are served by the API (`GET /api/playbooks`, `GET /api/playbooks/{slug}`) and
browsable in the dashboard's Venture Studio page. Venture agents cite them when a
scored idea matches a playbook's category.

| Slug | Playbook |
|------|----------|
| `ai-automation-agency` | AI automation agency |
| `saas-product` | SaaS product |
| `micro-saas` | Micro-SaaS |
| `trading-software` | Trading software business |
| `newsletter-content` | Newsletter / content business |
| `ecommerce-brand` | Ecommerce brand |
| `marketplace` | Marketplace |
| `b2b-service` | B2B service business |
| `ai-chatbot-product` | AI chatbot product |
| `local-business-automation` | Local business automation |
| `data-analytics-agency` | Data analytics agency |
| `nocode-productized-service` | No-code productized service |

**Numbers in playbooks are planning defaults, not promises** — replace them with
validated figures as soon as real data exists (the Memory system's
`financial_assumption` category is where validated figures live).
