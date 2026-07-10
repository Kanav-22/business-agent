# AI Business OS — Lumina Labs

A multi-agent system that runs a virtual company: a **CEO orchestrator** delegates to
C-suite specialist agents operating on real (currently synthetic) business data, surfaced
through a live dashboard. Built per [`BUSINESS_AGENT_SPEC.md`](./BUSINESS_AGENT_SPEC.md).

**Phase 4 (this repo state):** the company produces outward-facing work — with a
human gate. The CEO orchestrator fans out to **CFO, CMO, CTO, Researcher and
Workflow Coordinator** in parallel; the CFO leads a finance sub-team (**FP&A,
Reporting, Revenue, Control**) and the CMO now commissions a **Content** sub-agent
whose drafts land in an **Approvals inbox** — nothing is published without a click
(approving moves the draft to the Reports library). Monday mornings APScheduler runs
the Control agent's reconciliation check (06:00), the CEO briefing (06:20) and the
Researcher's competitor scan (06:40) without being asked. Dashboard: Overview (KPIs +
chart + latest briefing), Chat (live delegation tree), Agent Activity (runs with
tools, tokens, cost), Reports (read/download, run jobs on demand) and Approvals.

```
frontend/  Next.js 14 + TypeScript + Tailwind + Recharts
backend/   FastAPI + SQLAlchemy (SQLite) + Anthropic API agents
```

## Quick start

Requires Python 3.11+, Node 18+, and an Anthropic API key (only for chat — the
dashboard KPIs and all tests work without one).

### 1. Backend

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Seed the synthetic database (idempotent; --force to regenerate)
.venv/bin/python scripts/seed.py

# Run the API (chat needs the key; KPIs work without it)
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell — note `Scripts`, not `bin`; no `&&` in PowerShell 5.1, run
lines one at a time; no venv activation needed):

```powershell
cd backend
py -3 -m venv .venv        # or: python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python scripts\seed.py
$env:ANTHROPIC_API_KEY = "sk-ant-..."
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

The server auto-seeds on startup if the database is missing.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

If the backend runs elsewhere, copy `.env.local.example` to `.env.local` and set
`NEXT_PUBLIC_API_URL`.

### 3. Try it

Open http://localhost:3000 → **Overview** shows MRR, burn, runway, customers, open
tasks and the revenue/expense chart, all computed from SQL. Go to **Chat** and ask:

> *How is the business doing?*

You'll watch the CEO fan out to the CFO, CMO and CTO **in parallel**, each specialist
run its own `sql_query` calls (inputs and results expandable per tool call), and the
CEO synthesize a brief that attributes every finding to its source agent. Then check
**Agent Activity** for the run feed with per-run token usage and cost. Verify numbers
against `backend/data/lumina.db` — the dataset is deterministic and reconcilable.

Other good demos: *"Which invoices are overdue, and any unusual expenses this
month?"* (CFO → Revenue + Control in parallel), *"Produce a P&L report for last
month"* (CFO → Reporting, lands on the Reports page), *"Draft a launch announcement
for usage-based billing on the Scale tier"* (CMO → Content → **Approvals inbox**;
approve it there to publish), *"Which channel has the best CAC?"* (CMO), *"Are we on
track for the v2 launch?"* (CTO), *"What's blocked this week?"* (Coordinator),
*"What are competitors pricing at?"* (Researcher, uses Anthropic server-side web
search). On the **Reports** page you can trigger the Monday jobs on demand instead
of waiting for the schedule.

## Tests

```bash
cd backend
.venv/bin/python -m pytest
```

Covers:
- **Data reconciliation** — subscription revenue ↔ customers (billing/churn/expansion
  rules), payroll ↔ employees, marketing spend ↔ campaigns, invoices ↔ transactions,
  campaign conversions ≈ new signups, KPI sanity (positive cash & runway).
- **sql_query guardrails** — SELECT-only, table allowlist (sqlite authorizer +
  read-only connection), single statement, row limit.
- **python_calc sandbox** — import allowlist (math/statistics only), no file access,
  timeout, subprocess isolation.
- **Agent loop** — full CEO→specialist delegation with a scripted model client and
  *real* tool execution: event ordering, run parenting, token budget enforcement,
  delegation depth limit, JSONL decision logging.
- **Phase 2** — parallel fan-out to 3 specialists (results return in one message, in
  order), per-agent table allowlists, validated `create_task` writes, server-side web
  tool declarations, `pause_turn` resumption, activity feed assembly from logs.
- **Phase 3** — two-level delegation (CEO→CFO→FP&A) with parenting/depth asserts,
  `report_writer` validation and write-through, scheduled job functions saving
  control checks and briefings, reports API + download, manual job triggers.
- **Phase 4** — CEO→CMO→Content chain landing a pending approval (and nothing
  published), approve→publish / reject→archive endpoints incl. 409 on double
  decisions, `content_writer` validation, competitor-scan job.
- **API** — KPI/chart/activity/reports/approvals endpoints and the chat WebSocket
  stream.

## Architecture notes (Phase 1)

- **One `Agent` class, many configs** (`backend/app/agents/base.py`): a config is a
  system prompt + allowlisted tool subset + model. The CEO's only tools are
  `get_agent_roster` and `delegate_to_agent`. Specialists get their own registries:
  CFO → `sql_query` (finance tables) + `python_calc`; CMO → `sql_query` (campaigns/
  customers) + server-side `web_search`; CTO → `sql_query` (projects/tasks/employees);
  Researcher → server-side `web_search`/`web_fetch` only (no internal data);
  Coordinator → `sql_query` (tasks/employees) + validated `create_task`. Least
  privilege applies to table docs too — each agent only sees its own schema.
- **Parallel delegation**: all tool calls in one model turn run concurrently
  (`asyncio.gather`), so a broad question fans out to several specialists at once;
  their results return to the CEO in a single message, in call order.
- **The CFO mirrors the CEO one level down** (Phase 3): it holds only
  `delegate_to_agent` over its sub-team — FP&A (analysis/forecasts + `python_calc`),
  Reporting (`report_writer`), Revenue (invoices/AR/MRR movements), Control
  (reconciliation + anomaly checks) — and synthesizes with attribution. Depth is
  capped at 2 (CEO→CFO→sub-agent).
- **Agent writes stay behind validation**: `create_task` (Coordinator),
  `report_writer` (Reporting) and `content_writer` (Content) are deterministic code
  that validates every field before inserting — agents never write to the database
  directly.
- **Human-in-the-loop approvals** (Phase 4): the Content agent's only output path is
  `content_writer`, which files drafts as *pending* in the approvals inbox. Internal
  writes (tasks, reports) execute after validation, but outward-facing content
  requires a human click: approve publishes to the Reports library, reject archives
  it with a note, and a decided item can never be re-decided.
- **Scheduled operations** (`backend/app/scheduler.py`): APScheduler cron jobs run
  the Control check Mondays 06:00, the CEO briefing 06:20 and the Researcher's
  competitor scan 06:40 (server timezone); their runs stream to the JSONL logs (so
  they appear on the Activity page) and their outputs are persisted to the reports
  library. `POST /api/jobs/{name}/run` triggers any of them on demand; disable with
  `SCHEDULER_ENABLED=0`.
- **Deterministic code validates and executes** — agents never write to the DB. SQL is
  forced read-only at the sqlite level (URI `mode=ro` + authorizer callback), not by
  prompt. `python_calc` runs in an isolated subprocess with rlimits and a restricted
  builtin set.
- **Every agent decision is logged** to `backend/logs/decisions-YYYYMMDD.jsonl`:
  run start/end, every model text block, tool calls with inputs/outputs, token usage.
- **Guardrails**: per-request token budget shared across the delegation tree
  (`AGENT_TOKEN_BUDGET`, default 150k) and a delegation depth limit (2).
- **Pluggable data** (`backend/app/data/provider.py`): `SyntheticProvider` fills the
  schema today; a `RealBusinessProvider` (CSV/Stripe/accounting) implements the same
  interface in Phase 5 — agents never know the difference.

### Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for chat |
| `AGENT_MODEL` | `claude-sonnet-4-6` | Model for all agents |
| `AGENT_TOKEN_BUDGET` | `150000` | Max tokens per chat request (whole tree) |
| `DATA_SEED` | `7` | Synthetic data RNG seed |
| `BUSINESS_AGENT_DB` | `backend/data/lumina.db` | SQLite path |
| `BUSINESS_AGENT_LOGS` | `backend/logs` | JSONL decision logs |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |
| `SCHEDULER_ENABLED` | `1` | Monday auto-jobs (control check + briefing) |
| `NEXT_PUBLIC_API_URL` (frontend) | `http://localhost:8000` | Backend base URL |

## Roadmap

Phase 5: real data providers (`RealBusinessProvider`: CSV/Excel import, then
Stripe/accounting connectors), multi-tenant auth + per-business isolation, Postgres
migration. See the spec for definitions of done.
