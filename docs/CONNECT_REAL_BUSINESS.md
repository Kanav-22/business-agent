# Connecting a Real Business

The operations layer (CFO/CMO/CTO/Coordinator, KPIs, reconciliation,
briefings) currently reads the synthetic Lumina Labs dataset. This guide is
the practical path to pointing it at YOUR business. The venture layer needs
no connection — it already works on your inputs (ideas, founder profile,
memories).

Operations agents pick up the business profile at backend startup — restart after completing intake.

## The two paths

**Path A — load your data into the existing schema (available today).**
The agents don't know or care whether rows came from a generator or from
your bank export; they query tables. If you can produce CSVs, you can run
the OS on real data this week.

**Path B — `RealBusinessProvider` connectors (Phase 5, not yet built).**
A guided CSV/Excel mapping wizard, then Stripe / accounting connectors,
implementing the same `DataProvider` interface as the synthetic generator
(`backend/app/data/provider.py`). This is the productized version of Path A
— ask the architect for a V6 task packet when you want it built.

## Path A, step by step

### 1. Export from your systems

Minimum useful set: bank/accounting transactions, customer list, invoices.
Marketing campaigns, projects, employees, and a task list unlock the CMO,
CTO, and Coordinator respectively — add them when you have them.

### 2. Map to the schema (`backend/app/models.py` is the source of truth)

| Table | Required fields | Conventions that matter |
|---|---|---|
| `transactions` | date, type (`revenue`/`expense`), category, amount, description | category ∈ subscription/salary/cloud/tools/marketing/office (extend in your prompts if you add more); FKs (customer_id, employee_id, campaign_id) are nullable but power reconciliation |
| `customers` | name, plan, mrr, signup_date, churn_date (null = active) | mrr = CURRENT monthly price; billing assumed on the 1st; churn month unbilled |
| `invoices` | customer_id, transaction_id, amount, issue_date, due_date, status (`paid`/`issued`/`overdue`) | one invoice per subscription transaction |
| `campaigns` | name, channel, start/end dates, spend, leads, conversions | marketing transactions should sum to spend per campaign |
| `projects` | name, status (`planned`/`active`/`at_risk`/`completed`), owner_id, dates, description | CTO's world |
| `employees` | name, role, department, salary_annual, hire_date | monthly payroll expected ≈ salary_annual/12 |
| `tasks` | title, department, status (`open`/`in_progress`/`blocked`/`done`), blocked_reason | Coordinator's world |
| `meta` | key/value | **required keys**: `generated_at` (any ISO timestamp — its presence marks the DB as provisioned so the server won't overwrite it with synthetic data), `starting_cash`, `window_start`, `window_end` |

### 3. Load

Point the app at a fresh database and insert your rows with a small script
(pandas or plain SQLAlchemy). Skeleton:

```python
# backend/scripts/import_real.py  (adapt freely)
import datetime as dt, pandas as pd
from sqlalchemy.orm import Session
from app.db import make_engine
from app.models import Base, Transaction, Customer, Meta

engine = make_engine("data/mybusiness.db")
Base.metadata.create_all(engine)
with Session(engine) as s:
    for _, r in pd.read_csv("transactions.csv").iterrows():
        s.add(Transaction(date=dt.date.fromisoformat(r["date"]), type=r["type"],
                          category=r["category"], amount=float(r["amount"]),
                          description=str(r["description"])))
    # …customers, invoices, etc.…
    s.add_all([Meta(key="generated_at", value=dt.datetime.now().isoformat()),
               Meta(key="starting_cash", value="500000"),
               Meta(key="window_start", value="2025-07-01"),
               Meta(key="window_end", value="2026-06-30")])
    s.commit()
```

```bash
export BUSINESS_AGENT_DB=$PWD/data/mybusiness.db
python3 -m uvicorn app.main:app --port 8000
```

### 4. Expect the Control agent to complain — that's the feature

The synthetic data reconciles perfectly; real books never do. The Monday
control check (or `POST /api/jobs/weekly_control/run`) will flag
`[WARN]`/`[CRITICAL]` where billing ≠ customer MRR sums, payroll ≠
salaries/12, or campaign spend ≠ marketing transactions. Treat the first
run's flags as a data-quality worklist, not a bug. If a convention truly
doesn't fit your business (e.g. you bill mid-month), update the convention
text in the agent prompts (`service.py` `_FINANCE_CONVENTIONS`) to match
reality — the prompts describe the data contract.

### 5. Verify before trusting

- Overview KPIs match what you know (MRR, burn, cash).
- Ask the CFO for last month's profit; cross-check against your accounting.
- Run one full control check and resolve/accept each flag.

## Cautions

- **Privacy**: your books live in a local SQLite file; agents send query
  *results* to whatever model you configured. With a free cloud LLM, assume
  prompts may be used per that provider's terms — for sensitive books, use
  a local model (see `docs/FREE_LLM_SETUP.md`) or keep amounts coarse.
- Keep secrets (API keys, bank credentials) out of the database entirely.
- Reseeding warning: `python3 scripts/seed.py --force` DESTROYS the data in
  the configured DB and regenerates synthetic rows — never point it at your
  real DB file.
- One business per database today; run a second business as a second DB +
  port until multi-tenant (Phase 5) exists.

## Refresh cadence

Path A is snapshot-based: re-run your import weekly/monthly (idempotent if
you rebuild the file each time). The moment that ritual gets old is the
signal to commission Path B's connectors.
