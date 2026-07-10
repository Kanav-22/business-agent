# Memory System Design

What the Business OS remembers, when it saves, when it retrieves, and who can
touch what. The goal: a long-term operating system, not a goldfish chatbot.

## Architecture

Three memory stores already existed; this design adds the fourth and defines the
rules for all of them:

| Store | What it holds | Since |
|-------|---------------|-------|
| Business database (SQLite tables) | Operational facts: transactions, customers, campaigns, projects, tasks | Phase 1 |
| Reports library (`reports` table) | Generated documents: briefings, P&Ls, control checks, research, debates, simulations | Phase 3 |
| JSONL decision logs (`backend/logs/`) | Full audit trail of every agent run and tool call | Phase 1 |
| **Memory records (`memories` table)** | **Curated, retrievable knowledge: decisions, lessons, assumptions, research summaries** | **Venture layer** |

A memory record is short, structured, and written to be retrieved: `category`,
`title`, `content`, `source_agent`, optional `related_idea`, `status`
(active/archived), timestamps. Agents write memories through the validated
`save_memory` tool (category allowlist, size caps); humans and workflows read them
via `GET /api/memories`. Retrieval today is by category + recency + keyword;
vector retrieval is a documented future upgrade, not a dependency.

## The 16 memory categories

| # | Category (`category` value) | When to save | When to retrieve | How to update | How to delete |
|---|------------------------------|--------------|------------------|---------------|----------------|
| 1 | `founder_profile` | Founder edits the profile (stored in its own `founder_profile` table; mirrored here only on major changes) | Start of every venture workflow; router calls | Overwrite via `PUT /api/founder` | Profile keys can be blanked; history stays in logs |
| 2 | `business_idea` | An idea is scored (`score_idea` tool writes it automatically) | Before scoring a similar idea; pivot discussions | New score → new memory; old one stays for comparison | Archive when idea is rejected/absorbed |
| 3 | `active_business` | A business moves from idea to execution | Every workflow touching that business | Append status-change memories | Archive on shutdown/sale |
| 4 | `decision` | Debate workflow finalizes; any major go/no-go (auto-saved by `run_debate`) | Before revisiting the same topic; quarterly reviews | Decisions are immutable — supersede with a new decision memory referencing the old | Never delete; archive when superseded |
| 5 | `rejected_idea` | Idea scored NO-GO, or founder kills it | When a similar idea appears (prevents re-litigating) | Add the rejection reason | Never delete — this is the anti-distraction list |
| 6 | `customer_research` | Interview workflow completes (auto-saved); real customer calls summarized | Before positioning, pricing, copy work | Append new research; mark synthetic vs. real | Archive stale (>6 months) research |
| 7 | `competitor_research` | Researcher completes a competitor scan | Pricing, positioning, debate workflows | Append; date every claim | Archive when market shifts |
| 8 | `financial_assumption` | CFO states an assumption in a plan (CAC, margin, conversion) | Any forecast or plan using that number | Replace when validated with real data — note "validated" | Archive invalidated assumptions with the lesson |
| 9 | `product_roadmap` | MVP scope decided; phase completed | CTO planning; scope debates | Append phase changes | Archive on pivot |
| 10 | `marketing_experiment` | An experiment starts (hypothesis + budget) and again when it ends (result) | Before designing the next experiment | Close open experiments with results — an experiment without a recorded result is a bug | Never delete failures; they're the expensive lessons |
| 11 | `sales_conversation` | Notable prospect call: objections heard, exact words, close/loss reason | Copywriting, objection handling, ICP refinement | Append per conversation | Archive per closed/dead deal |
| 12 | `metric` | A KPI baseline or milestone worth remembering ("first ₹1L month") | Reviews, investor updates, debates | Append snapshots; never overwrite history | Don't — metrics history is the business's memoir |
| 13 | `risk` | Failure simulation completes (auto-saved); Risk Officer flags something material | Every major decision; weekly review | Update likelihood/severity as evidence arrives | Archive risks that closed harmlessly, with a note |
| 14 | `lesson_learned` | A postmortem, a surprising result, an expensive mistake | Start of any similar undertaking | Sharpen the lesson as understanding improves | Never delete |
| 15 | `board_meeting` | Debate workflow report saved (summary memory auto-linked to the full report) | Next board meeting on the same business; quarterly review | Immutable, like decisions | Never delete |
| 16 | `agent_performance` | Eval runs complete (summary); an agent output was materially wrong/great | Choosing models; tuning survival guides; router confidence | Append per eval run | Archive runs older than 2 model generations |

## Access matrix

| Agent / actor | Read | Write (via `save_memory` or automatic) |
|---------------|------|----------------------------------------|
| CEO | all categories | `decision` |
| CFO | financial_assumption, decision, metric, risk, business_idea | `financial_assumption` |
| CMO | customer_research, competitor_research, marketing_experiment, sales_conversation | `marketing_experiment` |
| CTO | product_roadmap, decision, risk | `product_roadmap` |
| COO | active_business, decision, lesson_learned, risk | `lesson_learned` |
| Risk Officer | risk, decision, rejected_idea | `risk` |
| Red Team | all (needs ammunition) | — (its output lands in reports) |
| Sales | sales_conversation, customer_research | `sales_conversation` |
| Interviewer | customer_research | `customer_research` (auto via workflow) |
| Researcher | competitor_research, customer_research | `competitor_research` |
| Workflows (deterministic code) | as needed | `decision`, `risk`, `customer_research`, `business_idea`, `board_meeting` (auto-saves) |
| Human (dashboard/API) | all | all + archive |

Enforcement note: writes are enforced by the `save_memory` tool's category
allowlist per agent. Reads are enforced socially (prompt-level) today — a
documented trade-off, acceptable because memory content is founder-owned, not
tenant-separated.

## Example records

```json
{"category": "decision", "title": "Doctors' tool: pilot, not launch",
 "content": "Debate 2026-07-10 decided 3-clinic pilot at ₹10k/mo instead of public launch. Owner: COO. Deadline: 21 days. Reverse if <2 clinics sign by day 10. Full report: #47.",
 "source_agent": "ceo", "related_idea": "ai-booking-doctors", "status": "active"}
```

```json
{"category": "rejected_idea", "title": "Generic AI resume builder — NO-GO (score 3.9)",
 "content": "Rejected 2026-07-10: competition 2/10, defensibility 2/10, distribution none. Revisit only with an owned audience. Score report: #52.",
 "source_agent": "scorer", "related_idea": "ai-resume-builder", "status": "active"}
```

```json
{"category": "financial_assumption", "title": "Clinic outreach → discovery-call rate: 15% (assumed)",
 "content": "Used in the 30-day plan. VALIDATE against first 40 calls; replace this memory with the measured rate.",
 "source_agent": "cfo", "related_idea": "ai-booking-doctors", "status": "active"}
```

## Retrieval protocol (what workflows actually do)

1. Venture workflow starts → load founder profile + active memories for the
   related idea (category-filtered, newest first, capped) and prepend them to the
   task brief.
2. Router receives a request → checks `rejected_idea` titles for overlap and says
   so in its routing note.
3. Debate/failure/interview/score workflows end → auto-save their memory record
   (deterministic code, not agent discretion).

## Future upgrades (documented, not built)

- Embedding-based retrieval over `content` when memories exceed a few hundred.
- Per-business namespacing when multi-tenant (Phase 5) lands.
- Memory summarization job: quarterly roll-up of `metric` and `lesson_learned`.
