# Prompt Routing Rules

The human-readable mirror of `backend/app/venture/router.py`. The router takes a
free-text request and returns: primary agent, supporting agents, workflow
sequence, reason, required inputs, expected output, and risk level. It is
deterministic (keyword rules), cheap, and auditable — the LLM-driven CEO routing
in chat stays untouched; this router powers the Venture Studio, the API
(`POST /api/route`), and pre-flight checks before workflows.

Risk levels: **low** (reversible, internal), **medium** (money or reputation at
stake), **high** (regulated domain, large capital, or irreversible).
High-risk categories always include the Risk Officer and recommend a debate
before commitment. If the founder profile is set, the router appends a
founder-fit note (e.g. budget vs. `budget_range`, distraction check vs.
`distracting_ideas`).

| # | Category | Primary | Supporting | Workflow sequence | Risk | Required inputs | Expected output |
|---|----------|---------|------------|-------------------|------|-----------------|-----------------|
| 1 | Business idea validation | ceo | scorer, researcher, red_team, interviewer | Idea Score → Synthetic Interviews → Red Team Review → Failure Simulation → Debate | medium | Idea description, budget, timeline, founder skills | Go / No-Go / Test-First with validation plan |
| 2 | Product building | cto | coo, researcher | MVP Scope → Build Plan → Weekly Checkpoints | medium | Validated idea, capacity, deadline | Scoped MVP + execution plan |
| 3 | Marketing | cmo | researcher, sales | Audience Definition → Channel Math → Experiment Design → Approvals | low | Target customer, budget, current numbers | Channel plan with CAC math + first experiment |
| 4 | Sales | sales | cmo | ICP Confirmation → Offer Design → Copy Draft → Approvals | low | ICP, offer, proof/assets available | Copy + objection handling + A/B variant |
| 5 | Finance | cfo | — | (operations: CFO sub-team routes internally) | low | The question + timeframe | Grounded numbers with attribution |
| 6 | Legal / compliance risk | risk | researcher | Risk Assessment → Professional-Review List → Mitigation Plan | high | Jurisdiction, data handled, claims made | Ranked risk register + verdict |
| 7 | Hiring | coo | cfo, risk | Role Definition → Cost Model → Hiring Plan | medium | Role, budget, timeline | Hire/don't-hire + plan with costs |
| 8 | Fundraising | ceo | cfo, researcher, risk | Readiness Check → Numbers Pack → Narrative → Red Team the Deck | high | Metrics, runway, raise target | Readiness verdict + materials plan |
| 9 | Customer support | coo | cto | Issue Triage → Process Fix → Automation Check | low | Issue volume, current process | Support process + automation candidates |
| 10 | Growth problems | cmo | cfo, researcher, red_team | Funnel Diagnosis → Bottleneck Math → Experiment Plan | medium | Funnel numbers, churn, CAC | Diagnosed bottleneck + ranked experiments |
| 11 | Pivot decisions | ceo | red_team, cfo, cmo, researcher | Debate → Failure Simulation (new direction) → Decision | high | Current traction, pivot hypothesis, runway | Pivot/persevere decision with reversal trigger |
| 12 | Market research | researcher | — | Research Brief → Cited Findings → Memory Save | low | The falsifiable question | Cited findings + confidence level |
| 13 | Technical architecture | cto | risk | Requirements → Buy-vs-Build → Architecture Note | medium | Scale expectations, team skills, budget | Stack decision + riskiest-component prototype plan |
| 14 | Trading / business risk | risk | cfo, red_team | Risk Assessment → Exposure Math → Debate (if proceeding) | high | Capital at risk, instruments/commitments, jurisdiction | Exposure register + proceed/don't verdict |
| 15 | Board meeting review | ceo | cfo, cmo, cto, coo, risk, researcher | Debate (full board) → Decision Memory → Report | medium | The proposal/period to review | Board-format report (9 sections) |

## Worked example

**User says:** "I want to launch an AI tool for doctors."

**Router output:**

```json
{
  "category": "business_idea_validation",
  "primary_agent": "ceo",
  "supporting_agents": ["researcher", "cto", "risk", "cmo"],
  "workflow": ["idea_score", "interviews", "red_team_review", "failure_sim", "debate"],
  "risk_level": "high",
  "reason": "New business idea in a regulated domain: healthcare terms detected, so the Risk Officer joins and a debate is required before any build commitment.",
  "required_inputs": ["idea description", "budget", "timeline", "founder skills (see founder profile)"],
  "expected_output": "Go / No-Go / Test-First verdict with a validation plan",
  "founder_fit_note": "Founder profile: risk tolerance 'medium', budget range '₹50k'. High-risk domain + small budget → recommend the Test-First path."
}
```

Note the escalation: the base category (idea validation) is medium risk, but the
healthcare keyword match raises it to high and pulls in `risk` — domain modifiers
(health, finance, legal, children, weapons, crypto/trading) override the base
level upward, never downward.

## Precedence rules

1. Domain risk modifiers apply after category matching (escalate only).
2. If several categories match, the highest-risk one wins the primary slot; the
   others' agents merge into supporting.
3. No category match → default to `ceo` (operations chat) at low risk, with a
   note that the request didn't match a venture category.
4. A `rejected_idea` memory whose title overlaps the request adds a warning to
   the routing note (the anti-distraction check).
