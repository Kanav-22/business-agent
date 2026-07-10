# Execution Dashboard Schema

The data model that makes the dashboard a command center for launching and
operating businesses. Covers the 10 operations tables that already existed, the
4 venture tables added by this layer, and 3 designed-but-not-yet-built entities
for the multi-business future.

Conventions: SQLite via SQLAlchemy (`backend/app/models.py`); agents read
through the SELECT-only `sql_query` tool with per-agent table allowlists; agents
write ONLY through validated tools (never raw SQL); humans read/write through
the dashboard APIs.

## A. Operations tables (existed before the venture layer — unchanged)

| Table | Key fields | Relationships | Read (agents) | Write | Dashboard surface | Execution value |
|-------|-----------|---------------|---------------|-------|-------------------|-----------------|
| `transactions` | date, type (revenue/expense), category, amount, description, FKs → customer/employee/campaign | explains every money movement | cfo team, cmo (marketing rows) | seeder only | Overview chart, KPIs | The financial ground truth every number reconciles to |
| `customers` | name, plan, mrr, signup_date, churn_date | ← transactions, invoices | cfo team, cmo | seeder only | KPI cards, (future) Customers view | MRR/churn/expansion truth |
| `invoices` | customer_id, transaction_id, amount, issue/due dates, status | one per subscription charge | revenue, control | seeder only | Reports (AR) | Collections and cash timing |
| `campaigns` | name, channel, dates, spend, leads, conversions | ← marketing transactions | cmo, control | seeder only | (future) Campaigns view | CAC by channel; experiment history |
| `projects` | name, status, owner_id, deadline, description | → employees | cto | seeder only | (future) Projects view | Delivery risk visibility |
| `employees` | name, role, department, salary_annual, hire_date | ← projects, tasks, payroll txns | cto, cfo team, coordinator | seeder only | (future) Team view | Capacity and payroll truth |
| `tasks` | title, department, status, assignee_id, due_date, blocked_reason | → employees | coordinator, cto | `create_task` tool | (future) Tasks view | The cross-department execution list |
| `meta` | key, value | dataset facts (window, starting cash) | all sql agents | seeder only | — | Deterministic date/cash anchors |
| `approvals` | kind, title, channel, agent, status, content, decided_at, note | → published reports | content (write via tool) | `content_writer` tool + human decision | Approvals inbox | Human gate on outward-facing work |
| `reports` | title, kind, agent, created_at, content | ← approvals publishing | reporting (write via tool) | `report_writer` + workflows | Reports library | The document memory of the business |

Report `kind` values now include the venture kinds: `report`, `briefing`,
`control_check`, `research`, `content` + `debate`, `failure_sim`, `interviews`,
`idea_score`, `eval`.

## B. Venture tables (added by this layer)

### `ideas`
| Field | Notes |
|-------|-------|
| id, title, description | the idea as stated |
| scores_json | 14 category scores (1–10) + per-category rationale |
| total_score | weighted average, 1 decimal |
| verdict | `go` / `no_go` / `test_first` — computed deterministically |
| best_version, worst_risk, validation_test, next_actions | scorer's structured outputs |
| created_at | scoring time |

Relationships: `memories.related_idea` (soft key), score report in `reports`.
Read: all venture agents + human. Write: `score_idea` tool only.
Dashboard: Venture Studio idea scoreboard (verdict badges, score breakdown).
Value: kills bad ideas cheaply and keeps the comparison history.

### `memories`
| Field | Notes |
|-------|-------|
| id, category | one of the 16 categories in `docs/MEMORY_SYSTEM.md` |
| title, content | short, written-to-be-retrieved |
| source_agent | who saved it |
| related_idea | soft link to an idea/business slug |
| status | `active` / `archived` |
| created_at, updated_at | |

Read: per the access matrix in MEMORY_SYSTEM.md. Write: `save_memory` tool
(validated) + workflow auto-saves + human API.
Dashboard: Venture Studio memories browser (filter by category).
Value: decisions, lessons, and research survive across sessions and models.

### `founder_profile`
| Field | Notes |
|-------|-------|
| key | one of the 16 keys in `docs/FOUNDER_CLONE_TEMPLATE.md` |
| value | free text |
| updated_at | |

Read: router + all venture workflows (prepended to briefs). Write: human only
(`PUT /api/founder`).
Dashboard: Venture Studio founder profile editor.
Value: every recommendation becomes founder-specific; the "clone" that survives
model downgrades.

### `eval_results`
| Field | Notes |
|-------|-------|
| id, case_id | which eval case ran |
| agent, model | who was tested, on which model |
| score (0–10), passed (bool) | rubric outcome |
| details_json | per-criterion breakdown + improvement suggestions |
| created_at | |

Read: human, `agent_performance` memory summaries. Write: eval runner only.
Dashboard: (API now, page later) — model-comparison scoreboard.
Value: proves whether a cheaper/weaker model is good enough, per agent.

## C. Designed, not yet built (for the multi-business future)

| Entity | Purpose | Sketch |
|--------|---------|--------|
| `businesses` | When one OS runs several ventures: id, name, playbook_slug, stage (idea/pilot/active/closed), started_at. Everything else gains a `business_id`. | Prerequisite for Phase 5 multi-tenant |
| `experiments` | First-class experiment tracking beyond memory records: hypothesis, metric, budget, start/end, result, decision. Today: `marketing_experiment` memories. | Add when experiments exceed ~10/month |
| `meetings` | Scheduled board meetings with agenda + attendance beyond debate reports. Today: `reports(kind='debate')` + `board_meeting` memories. | Add with calendar integration |

## D. How the schema serves execution

- **One writer per table**: every table has exactly one validated write path —
  the audit question "who wrote this row?" always has an answer.
- **Soft keys for venture data** (`related_idea` as slug): ideas die too often to
  justify FK ceremony; operations data keeps hard FKs because it reconciles.
- **Reports are the narrative layer, tables the factual layer**: the dashboard
  shows tables for state and reports for reasoning.
- **Everything the 16 requested entities need is mapped**: Businesses (§C),
  Ideas (`ideas`), Agents (roster + activity logs), Tasks (`tasks`), Decisions
  (`memories:decision` + debate reports), Experiments (§C + memories), Metrics
  (KPI API + `memories:metric`), Customers (`customers`), Campaigns
  (`campaigns`), Financials (`transactions`/`invoices`), Risks
  (`memories:risk` + failure sims), Research notes (`reports:research` +
  memories), Meetings (`reports:debate`), Playbooks (`docs/playbooks` via API),
  Evaluations (`eval_results`), Memories (`memories`).
