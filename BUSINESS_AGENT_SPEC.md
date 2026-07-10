# AI Business OS — Build Spec for Claude Code

A multi-agent system that runs a virtual company: a CEO orchestrator delegating to C-suite specialist agents (CFO, CTO, CMO, Researcher, plus their sub-teams), operating on business data, surfaced through a web dashboard.

**Ground rules for Claude Code sessions:**
- Build ONE phase at a time. Do not scaffold future phases.
- After each phase: everything runs, tests pass, commit.
- LLM agents propose and analyze; deterministic code validates and executes. No agent writes directly to the database without passing validation.
- Log every agent decision (inputs, outputs, tool calls) to JSONL for auditability.

---

## 1. Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | Python 3.11+, FastAPI | Async, WebSocket support for live agent streams |
| Agents | Anthropic API (claude-sonnet-4-6), tool use | Orchestrator + specialists pattern |
| DB | SQLite via SQLAlchemy | Zero-ops now; swap to Postgres later without code changes |
| Frontend | Next.js 14 + TypeScript + Tailwind + shadcn/ui | Dashboard from day one |
| Charts | Recharts | Simple, good-looking |
| Realtime | WebSockets (FastAPI native) | Watch agents work live |
| Jobs | APScheduler | Weekly reports, scheduled agent runs |

---

## 2. Architecture

```
┌─────────────────────  Next.js Dashboard  ─────────────────────┐
│  Overview │ Chat with CEO │ Agent Activity │ Reports │ Data   │
└───────────────────────────┬───────────────────────────────────┘
                     REST + WebSocket
┌───────────────────────────┴───────────────────────────────────┐
│                        FastAPI Backend                         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    CEO Orchestrator                       │ │
│  │   parses request → plans → delegates → synthesizes        │ │
│  └───┬──────────┬──────────┬──────────┬──────────┬──────────┘ │
│      │          │          │          │          │            │
│    CFO        CMO        CTO      Researcher  Workflow        │
│      │          │                              Coordinator    │
│  ┌───┴───┐  ┌───┴────┐                                        │
│  │FP&A   │  │Content │   (sub-agents, Phase 3+)               │
│  │Report │  │Social  │                                        │
│  │Revenue│  └────────┘                                        │
│  │Control│                                                    │
│  └───────┘                                                    │
│                     Shared Tool Registry                       │
│   sql_query │ python_calc │ report_writer │ web_search │ ...  │
└───────────────────────────┬───────────────────────────────────┘
                      SQLAlchemy (pluggable)
                    ┌─────────┴─────────┐
                    │   SQLite (demo)   │  ← later: Postgres, real
                    │ transactions,     │    accounting exports,
                    │ customers, tasks… │    Stripe API, etc.
                    └───────────────────┘
```

### Agent design principles
- Every agent = system prompt + allowed tool subset + model call. One class, many configs.
- The CEO never answers domain questions itself — it routes, then synthesizes specialist answers.
- Each specialist has ONLY the tools it needs (CFO gets sql_query on finance tables; CMO gets web_search + content tools). Least privilege.
- Agent runs are async tasks; progress streams over WebSocket to the dashboard.

---

## 3. Data Layer (Pluggable — this is important)

Define a `DataProvider` interface. Phase 1 ships `SyntheticProvider`; a future `RealBusinessProvider` (CSV import, Stripe, accounting exports) implements the same interface. Agents never know the difference.

### Synthetic dataset: "Lumina Labs" — a fictional 12-person SaaS company
Generate 18 months of realistic, internally consistent data:
- `transactions` — revenue (MRR from ~140 customers, some churn/expansion) and expenses (salaries, cloud, tools, marketing spend) with realistic seasonality
- `customers` — plan tier, signup date, churn date (nullable), MRR
- `invoices` — issued/paid/overdue states
- `campaigns` — marketing campaigns with spend, channel, leads, conversions
- `projects` — engineering projects with status, deadlines (for the CTO)
- `employees` — roles, salaries, departments
- `tasks` — cross-department task list the Workflow Coordinator manages

Consistency requirement: MRR in transactions must reconcile with the customers table; campaign conversions must roughly correspond to new customers. The Control agent will be checking this — the data must be checkable.

---

## 4. The Agents

| Agent | Role | Tools | Example query it handles |
|-------|------|-------|--------------------------|
| **CEO (orchestrator)** | Route, plan multi-agent tasks, synthesize | delegate_to_agent, get_agent_roster | "How's the business doing?" |
| **CFO** | Financial analysis, budgets, forecasts | sql_query (finance tables), python_calc | "What's our runway?" |
| ↳ FP&A (Phase 3) | Budget vs actual, forecasting | sql_query, python_calc | "Forecast Q4 revenue" |
| ↳ Reporting (Phase 3) | Formal report docs | report_writer, chart_spec | "Monthly P&L report" |
| ↳ Revenue (Phase 3) | AR, invoices, MRR movements | sql_query (invoices, customers) | "Which invoices are overdue?" |
| ↳ Control (Phase 3) | Anomaly + reconciliation checks | sql_query, python_calc | "Any unusual expenses this month?" |
| **CMO** | Marketing performance, strategy | sql_query (campaigns), web_search | "Which channel has best CAC?" |
| ↳ Content (Phase 4) | Drafts posts, emails, copy | web_search, content_writer | "Draft launch announcement" |
| **CTO** | Project status, resourcing | sql_query (projects, employees) | "Are we on track for the v2 launch?" |
| **Researcher** | External research, competitors, market | web_search, web_fetch | "What are competitors pricing at?" |
| **Workflow Coordinator** | Task tracking, scheduling agent runs | sql_query (tasks), create_task, schedule_run | "What's blocked this week?" |

### Tool registry (shared)
- `sql_query(query, allowed_tables)` — SELECT-only, table allowlist per agent, row limit
- `python_calc(code)` — sandboxed numeric computation (restricted builtins)
- `report_writer(title, sections)` — renders markdown report, saved + downloadable
- `chart_spec(type, data_query, options)` — returns a spec the frontend renders with Recharts
- `web_search(query)` / `web_fetch(url)` — Researcher + CMO only
- `delegate_to_agent(agent, task)` — CEO only
- `create_task(...)`, `schedule_run(...)` — Workflow Coordinator only

---

## 5. Dashboard (Next.js)

Pages:
1. **Overview** — KPI cards (MRR, burn, runway, active customers, open tasks) + revenue/expense chart. Auto-generated weekly "CEO briefing" summary at top.
2. **Chat** — talk to the CEO agent. Shows the delegation tree live: CEO → CFO → answer, streaming over WebSocket, with expandable tool-call details.
3. **Agent Activity** — feed of all agent runs: who ran, why, what tools they called, cost (token usage), duration.
4. **Reports** — generated reports library (view/download markdown or PDF).
5. **Data** — browse the underlying tables; button to regenerate synthetic data; (later) import real data.

Design: dark, clean, "mission control" feel. Sidebar nav. Each agent has a color + avatar so the delegation tree is readable.

---

## 6. Build Phases (each = one Claude Code session)

### Phase 1 — Skeleton + one real agent (this is the milestone that matters)
- Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js)
- Synthetic data generator for Lumina Labs (all tables, reconcilable)
- Agent core: base `Agent` class, tool registry, JSONL logging
- **CFO agent only**, with sql_query + python_calc
- CEO orchestrator that routes to CFO (roster of one)
- Dashboard: Overview page (KPIs from real queries) + Chat page (WebSocket streaming, delegation shown)
- DoD: I open the dashboard, ask "what was our profit last month and what's our runway?", watch CEO delegate to CFO, get a correct answer verifiable against the data.

**Phase 1 prompt for Claude Code:**
> Read BUSINESS_AGENT_SPEC.md. Build Phase 1 exactly as specified: FastAPI backend + Next.js dashboard, synthetic data generator for the Lumina Labs dataset (make transactions reconcile with customers), Agent base class with tool registry and JSONL decision logging, a CFO agent with SELECT-only sql_query (finance tables allowlist) and sandboxed python_calc, a CEO orchestrator that delegates to it, WebSocket streaming of the delegation to a Chat page, and an Overview page with KPI cards and a revenue/expense chart. Include a seed script, run instructions, and a test that verifies the synthetic data reconciles.

### Phase 2 — Full C-suite
- Add CMO, CTO, Researcher, Workflow Coordinator agents
- CEO learns multi-agent plans: "how's the business?" → parallel delegation to CFO+CMO+CTO → synthesized brief
- Agent Activity page
- DoD: one question fans out to 3+ agents in parallel, dashboard shows the tree, synthesis cites which agent said what.

### Phase 3 — CFO sub-team + scheduled operations
- Split CFO into FP&A, Reporting, Revenue, Control sub-agents (matches the diagram that inspired this)
- Control agent runs weekly reconciliation + anomaly checks automatically (APScheduler)
- Reports page + report_writer tool; weekly auto-generated CEO briefing
- DoD: Monday morning the system has already produced a weekly briefing and flagged anomalies without being asked.

### Phase 4 — Marketing team + outward-facing work
- Content sub-agent (drafts posts/emails), Researcher does competitor scans on schedule
- Human-in-the-loop approval queue: content/tasks agents propose land in an "Approvals" inbox — nothing external happens without a click
- DoD: CMO proposes a campaign, Content drafts it, it sits in approvals until I approve.

### Phase 5 — Real data
- `RealBusinessProvider`: CSV/Excel import mapping wizard, then Stripe/accounting API connectors
- Multi-tenant if selling to clients (auth, per-business data isolation)
- Postgres migration
- This phase turns the project into the SaaS from your master plan (Project 5).

---

## 7. Safety & Cost Guardrails
- All SQL is SELECT-only through the tool; writes go through typed, validated endpoints
- python_calc sandbox: no imports beyond math/statistics, no file/network access, timeout
- Per-run token budget; orchestrator depth limit (max 2 levels of delegation) to prevent runaway loops
- Track and display API cost per agent run on the Activity page — you'll learn fast which designs are expensive
- Approvals queue (Phase 4) before anything leaves the system

---

## 8. What Success Looks Like
Phase 2 finished = a genuinely impressive portfolio piece (demo video: ask one question, watch five executives work in parallel). Phase 3 = the finance diagram from the original inspiration, fully realized. Phase 5 = a sellable product.
