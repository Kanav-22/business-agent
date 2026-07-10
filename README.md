# AI Business OS — Lumina Labs

A multi-agent system that runs a virtual company: a **CEO orchestrator** delegates to
C-suite specialist agents operating on real (currently synthetic) business data, surfaced
through a live dashboard. Built per [`BUSINESS_AGENT_SPEC.md`](./BUSINESS_AGENT_SPEC.md).

**Phase 1 (this repo state):** CEO → CFO delegation over WebSocket, a reconcilable
synthetic dataset for "Lumina Labs" (a fictional 12-person SaaS company), and a dashboard
with Overview (KPIs + revenue/expense chart) and Chat (live delegation tree) pages.

```
frontend/  Next.js 14 + TypeScript + Tailwind + Recharts
backend/   FastAPI + SQLAlchemy (SQLite) + Anthropic API agents
```

## Quick start

Requires Python 3.11+, Node 18+, and an Anthropic API key (only for chat — the
dashboard KPIs and all tests work without one).

### 1. Backend

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

> *What was our profit last month and what's our runway?*

You'll watch the CEO delegate to the CFO, the CFO run `sql_query`/`python_calc`
(inputs and results expandable per tool call), and the CEO synthesize the answer.
Verify the numbers yourself against `backend/data/lumina.db` — the dataset is
deterministic and reconcilable.

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
- **Agent loop** — full CEO→CFO delegation with a scripted model client and *real*
  tool execution: event ordering, run parenting, token budget enforcement, delegation
  depth limit, JSONL decision logging.
- **API** — KPI/chart endpoints and the chat WebSocket stream.

## Architecture notes (Phase 1)

- **One `Agent` class, many configs** (`backend/app/agents/base.py`): a config is a
  system prompt + allowlisted tool subset + model. The CEO's only tools are
  `get_agent_roster` and `delegate_to_agent`; the CFO gets `sql_query` (finance tables
  only) and `python_calc`. Least privilege throughout.
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
| `NEXT_PUBLIC_API_URL` (frontend) | `http://localhost:8000` | Backend base URL |

## Roadmap

Phase 2: full C-suite (CMO, CTO, Researcher, Workflow Coordinator) with parallel
delegation + Agent Activity page · Phase 3: CFO sub-team, scheduled reconciliation,
reports · Phase 4: approvals inbox for outward-facing work · Phase 5: real data
providers, multi-tenant, Postgres. See the spec for definitions of done.
