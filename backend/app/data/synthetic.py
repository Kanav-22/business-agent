"""Synthetic dataset generator for "Lumina Labs", a fictional 12-person SaaS company.

Generates 18 months of internally consistent data. The consistency rules are
load-bearing — the reconciliation tests (and, in Phase 3, the Control agent)
verify them:

1. Billing rule: a customer is billed PLAN price on the 1st of every month from
   their signup month through the month before churn_date. Churn dates are
   always the 1st of a month. One 'subscription' transaction per billed month.
2. Expansion only: a customer's monthly amount never decreases, and
   customers.mrr always equals the amount of their most recent billed month.
3. One invoice per subscription transaction, same amount.
4. One 'salary' transaction per employee per month from their hire month,
   amount = round(salary_annual / 12, 2).
5. Per campaign: the sum of its 'marketing' transactions equals campaigns.spend.
6. Campaign conversions roughly correspond to new signups: total conversions
   is 55–80% of in-window signups (the rest is organic).
"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.data.provider import DataProvider
from app.models import (
    Base,
    Campaign,
    Customer,
    Employee,
    Invoice,
    Meta,
    Project,
    Task,
    Transaction,
)

PLAN_PRICES: dict[str, float] = {"starter": 99.0, "growth": 299.0, "scale": 899.0}
PLAN_ORDER = ["starter", "growth", "scale"]
STARTING_CASH = 3_200_000.00
N_MONTHS = 18

_ADJECTIVES = [
    "Nimbus", "Vertex", "Harbor", "Cinder", "Atlas", "Beacon", "Quartz", "Solstice",
    "Drift", "Ember", "Fable", "Granite", "Halcyon", "Iris", "Juniper", "Kestrel",
    "Lattice", "Meridian", "Northwind", "Opal", "Pioneer", "Riverbed", "Summit", "Tundra",
]
_NOUNS = [
    "Analytics", "Robotics", "Logistics", "Media", "Health", "Foods", "Legal",
    "Studios", "Security", "Learning", "Commerce", "Fintech", "Mobility", "Energy",
    "Biotech", "Retail", "Works", "Systems",
]

_EMPLOYEES = [
    # (name, role, department, annual salary, months hired BEFORE window start (>=0) or -index into window)
    ("Maya Lindqvist", "CEO & Co-founder", "Leadership", 150_000, "pre", 30),
    ("Daniel Okafor", "CTO & Co-founder", "Engineering", 150_000, "pre", 30),
    ("Priya Raman", "Senior Engineer", "Engineering", 138_000, "pre", 14),
    ("Tomás Herrera", "Senior Engineer", "Engineering", 132_000, "window", 3),
    ("Alice Zhang", "Engineer", "Engineering", 112_800, "window", 6),
    ("Yusuf Demir", "Engineer", "Engineering", 106_800, "window", 10),
    ("Hannah Blake", "Product Designer", "Product", 100_800, "pre", 10),
    ("Marco Rossi", "Product Manager", "Product", 115_200, "window", 2),
    ("Sofia Anders", "Head of Marketing", "Marketing", 120_000, "pre", 8),
    ("Jordan Miles", "Growth Marketer", "Marketing", 94_800, "pre", 4),
    ("Lena Petrova", "Customer Success Lead", "Customer Success", 76_800, "window", 5),
    ("Sam Whitaker", "Ops & Finance", "Operations", 85_200, "window", 8),
]

_CHANNELS = ["Google Ads", "LinkedIn", "Content", "X/Twitter", "Webinar", "Conference"]

_PROJECTS = [
    ("Platform v2", "active", "Rebuild of the core analytics engine on the new event pipeline."),
    ("SSO & RBAC", "active", "Enterprise single sign-on plus role-based access control."),
    ("Usage-based billing", "at_risk", "Metered billing to support the new Scale tier pricing."),
    ("Mobile companion app", "planned", "Read-only iOS/Android dashboards for on-call execs."),
    ("Data pipeline rework", "completed", "Move nightly batch jobs to streaming ingestion."),
    ("AI insights assistant", "active", "Natural-language Q&A over customer dashboards."),
    ("SOC 2 Type II", "at_risk", "Audit readiness: logging, access reviews, vendor policies."),
    ("Onboarding revamp", "completed", "Self-serve setup flow; cut time-to-first-dashboard to 10 min."),
]

_TASKS = [
    ("Close Q2 books and send investor update", "Operations", "in_progress", None),
    ("Renew AWS savings plan before expiry", "Operations", "open", None),
    ("Prepare board deck for July meeting", "Leadership", "open", None),
    ("Fix flaky ingestion integration tests", "Engineering", "in_progress", None),
    ("Ship usage-based billing meter API", "Engineering", "blocked", "Waiting on pricing sign-off from Leadership"),
    ("Load-test Platform v2 event pipeline", "Engineering", "open", None),
    ("Rotate production database credentials", "Engineering", "done", None),
    ("SOC 2 evidence collection: access reviews", "Engineering", "blocked", "Vendor questionnaire pending from auditor"),
    ("Migrate marketing site to new CMS", "Marketing", "in_progress", None),
    ("Draft launch post for AI insights beta", "Marketing", "open", None),
    ("Q3 webinar series calendar", "Marketing", "open", None),
    ("Refresh case study with Meridian Fintech", "Marketing", "done", None),
    ("Audit Google Ads negative keywords", "Marketing", "done", None),
    ("Onboard the five June enterprise signups", "Customer Success", "in_progress", None),
    ("Build churn-risk health score v1", "Customer Success", "blocked", "Needs product usage events from Data pipeline rework"),
    ("QBR schedule for top 15 accounts", "Customer Success", "open", None),
    ("Update security questionnaire template", "Operations", "done", None),
    ("Hire backend engineer (headcount #13)", "Leadership", "in_progress", None),
    ("Negotiate annual contract with data vendor", "Operations", "blocked", "Vendor legal redlines still open"),
    ("Design mobile app navigation prototype", "Product", "in_progress", None),
    ("Spec usage-based billing plan tiers", "Product", "done", None),
    ("Customer interviews: AI assistant beta", "Product", "open", None),
    ("Write RBAC permission matrix docs", "Product", "open", None),
    ("Clean up stale feature flags", "Engineering", "open", None),
    ("Upgrade Postgres to 16 on staging", "Engineering", "done", None),
    ("Instrument funnel analytics on signup flow", "Engineering", "in_progress", None),
    ("Plan EU data-residency approach", "Leadership", "open", None),
    ("Refresh pricing page with Scale tier", "Marketing", "in_progress", None),
    ("Set up quarterly OKR check-in ritual", "Leadership", "done", None),
    ("Expand status page monitoring checks", "Engineering", "open", None),
]


def month_floor(d: dt.date) -> dt.date:
    return d.replace(day=1)


def add_months(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.year * 12 + (d.month - 1) + n, 12)
    return dt.date(y, m + 1, d.day)


def month_key(d: dt.date) -> str:
    return d.strftime("%Y-%m")


@dataclass
class _Cust:
    id: int
    name: str
    signup: dt.date
    churn: dt.date | None = None
    # (effective month, plan) — append-only, upgrades only
    plan_history: list[tuple[dt.date, str]] = field(default_factory=list)

    def plan_at(self, month: dt.date) -> str:
        plan = self.plan_history[0][1]
        for eff, p in self.plan_history:
            if eff <= month:
                plan = p
        return plan

    def billed_in(self, month: dt.date) -> bool:
        if month_floor(self.signup) > month:
            return False
        return self.churn is None or self.churn > month


class SyntheticProvider(DataProvider):
    """Deterministic generator: same (seed, anchor) → byte-identical dataset."""

    name = "synthetic"

    def __init__(self, seed: int = 7, anchor: dt.date | None = None):
        self.seed = seed
        # anchor = first day of the month AFTER the last data month.
        self.anchor = month_floor(anchor or dt.date.today())

    # ------------------------------------------------------------------ public

    def provision(self, engine: Engine, *, force: bool = False) -> dict:
        Base.metadata.create_all(engine)
        if not force and self.is_provisioned(engine):
            return {"skipped": True}
        rows = self._generate()
        with Session(engine) as session:
            for table in (Invoice, Transaction, Task, Project, Campaign, Customer, Employee, Meta):
                session.execute(delete(table))
            for objs in rows.values():
                session.add_all(objs)
            session.commit()
            summary = {name: len(objs) for name, objs in rows.items()}
        summary["skipped"] = False
        return summary

    # ---------------------------------------------------------------- internal

    def _generate(self) -> dict[str, list]:
        rng = random.Random(self.seed)
        months = [add_months(self.anchor, -N_MONTHS + i) for i in range(N_MONTHS)]
        window_start, window_end = months[0], add_months(months[-1], 1) - dt.timedelta(days=1)

        customers = self._gen_customers(rng, months)
        employees = self._gen_employees(months)
        campaigns, mkt_txns = self._gen_campaigns(rng, months, customers)

        txns: list[Transaction] = []
        invoices: list[Invoice] = []
        txn_id = 0

        # --- subscription revenue + invoices (rule 1, 2, 3)
        for m_idx, m in enumerate(months):
            for c in customers:
                if not c.billed_in(m):
                    continue
                txn_id += 1
                amount = PLAN_PRICES[c.plan_at(m)]
                txns.append(
                    Transaction(
                        id=txn_id, date=m, type="revenue", category="subscription",
                        amount=amount, description=f"Subscription — {c.name}",
                        customer_id=c.id,
                    )
                )
                invoices.append(
                    Invoice(
                        id=txn_id, customer_id=c.id, transaction_id=txn_id,
                        amount=amount, issue_date=m, due_date=m + dt.timedelta(days=14),
                        status=self._invoice_status(rng, m_idx),
                    )
                )

        # --- salaries (rule 4)
        for m in months:
            for e in employees:
                if e.hire_date > m:
                    continue
                txn_id += 1
                pay_date = add_months(m, 1) - dt.timedelta(days=1)
                txns.append(
                    Transaction(
                        id=txn_id, date=pay_date, type="expense", category="salary",
                        amount=round(e.salary_annual / 12, 2),
                        description=f"Salary — {e.name}", employee_id=e.id,
                    )
                )

        # --- marketing spend, tied to campaigns (rule 5)
        for t in mkt_txns:
            txn_id += 1
            t.id = txn_id
            txns.append(t)

        # --- cloud / tools / office with growth + noise
        for m in months:
            active_customers = sum(1 for c in customers if c.billed_in(m))
            active_employees = sum(1 for e in employees if e.hire_date <= m)
            cloud = (1800 + 26 * active_customers) * rng.uniform(0.93, 1.09)
            tools = (1400 + 85 * active_employees) * rng.uniform(0.95, 1.06)
            office = 3200 + rng.uniform(-220, 260)
            for cat, amount, day, desc in (
                ("cloud", cloud, 3, "AWS + data infrastructure"),
                ("tools", tools, 5, "SaaS tooling (GitHub, Figma, HubSpot…)"),
                ("office", office, 15, "Office, insurance & misc"),
            ):
                txn_id += 1
                txns.append(
                    Transaction(
                        id=txn_id, date=m.replace(day=day), type="expense",
                        category=cat, amount=round(amount, 2), description=desc,
                    )
                )

        projects = self._gen_projects(rng, months, employees)
        tasks = self._gen_tasks(rng, months, employees)

        customer_rows = [
            Customer(
                id=c.id, name=c.name, plan=c.plan_history[-1][1],
                mrr=PLAN_PRICES[c.plan_history[-1][1]],
                signup_date=c.signup, churn_date=c.churn,
            )
            for c in customers
        ]

        meta = [
            Meta(key="company", value="Lumina Labs"),
            Meta(key="starting_cash", value=f"{STARTING_CASH:.2f}"),
            Meta(key="window_start", value=window_start.isoformat()),
            Meta(key="window_end", value=window_end.isoformat()),
            Meta(key="months", value=str(N_MONTHS)),
            Meta(key="seed", value=str(self.seed)),
            Meta(key="generated_at", value=self.anchor.isoformat()),
            Meta(key="provider", value=self.name),
        ]

        return {
            "customers": customer_rows,
            "employees": employees,
            "campaigns": campaigns,
            "transactions": txns,
            "invoices": invoices,
            "projects": projects,
            "tasks": tasks,
            "meta": meta,
        }

    def _gen_customers(self, rng: random.Random, months: list[dt.date]) -> list[_Cust]:
        names = [f"{a} {n}" for a in _ADJECTIVES for n in _NOUNS]
        rng.shuffle(names)
        name_iter = iter(names)

        def pick_plan() -> str:
            r = rng.random()
            return "starter" if r < 0.55 else ("growth" if r < 0.88 else "scale")

        customers: list[_Cust] = []
        next_id = 0

        # 45 customers acquired before the window opens.
        for _ in range(45):
            next_id += 1
            signup = add_months(months[0], -rng.randint(1, 14)).replace(day=rng.randint(1, 28))
            c = _Cust(id=next_id, name=next(name_iter), signup=signup)
            c.plan_history.append((month_floor(signup), pick_plan()))
            customers.append(c)

        for m_idx, m in enumerate(months):
            # churn: skip month 0 so every customer bills at least once in-window
            if m_idx > 0:
                for c in customers:
                    if c.churn is not None or month_floor(c.signup) >= m:
                        continue
                    if rng.random() < 0.015:
                        c.churn = m
            # expansions: tenured, non-scale, still active
            for c in customers:
                if c.churn is not None or c.plan_history[-1][1] == "scale":
                    continue
                if add_months(month_floor(c.signup), 4) <= m and rng.random() < 0.012:
                    cur = c.plan_history[-1][1]
                    c.plan_history.append((m, PLAN_ORDER[PLAN_ORDER.index(cur) + 1]))
            # new signups: ramping base + seasonality (Jan bump, light Sep/Oct bump)
            base = 4 + round(4 * m_idx / (N_MONTHS - 1))
            bump = 2 if m.month == 1 else (1 if m.month in (9, 10) else 0)
            for _ in range(base + bump + rng.randint(0, 2)):
                next_id += 1
                signup = m.replace(day=rng.randint(1, 28))
                c = _Cust(id=next_id, name=next(name_iter), signup=signup)
                c.plan_history.append((m, pick_plan()))
                customers.append(c)
        return customers

    @staticmethod
    def _gen_employees(months: list[dt.date]) -> list[Employee]:
        rows = []
        for i, (name, role, dept, salary, kind, offset) in enumerate(_EMPLOYEES, start=1):
            hire = add_months(months[0], -offset) if kind == "pre" else months[offset]
            rows.append(
                Employee(id=i, name=name, role=role, department=dept,
                         salary_annual=float(salary), hire_date=hire)
            )
        return rows

    def _gen_campaigns(
        self, rng: random.Random, months: list[dt.date], customers: list[_Cust]
    ) -> tuple[list[Campaign], list[Transaction]]:
        # Lay out campaigns so every month has at least one active.
        specs: list[dict] = []  # {name, channel, start_idx, n_months, monthly_spend}
        cid = 0
        for m_idx, m in enumerate(months):
            active = sum(1 for s in specs if s["start_idx"] <= m_idx < s["start_idx"] + s["n_months"])
            want = 1 + (1 if rng.random() < 0.35 else 0)
            for _ in range(max(0, want - active)):
                cid += 1
                channel = rng.choice(_CHANNELS)
                n = rng.randint(1, 3)
                if m_idx + n > N_MONTHS:
                    n = N_MONTHS - m_idx
                specs.append({
                    "id": cid,
                    "name": f"{channel} — {m.strftime('%b %Y')} push",
                    "channel": channel,
                    "start_idx": m_idx,
                    "n_months": n,
                    "monthly_spend": float(rng.randrange(2000, 8500, 500)),
                })

        # Attribute a 55–80% share of each month's signups to active campaigns,
        # split proportionally to spend (largest remainder so counts are exact).
        conversions = {s["id"]: 0 for s in specs}
        for m_idx, m in enumerate(months):
            signups = sum(1 for c in customers if month_floor(c.signup) == m)
            attributed = int(round(signups * rng.uniform(0.55, 0.80)))
            active = [s for s in specs if s["start_idx"] <= m_idx < s["start_idx"] + s["n_months"]]
            if not active or attributed == 0:
                continue
            total_spend = sum(s["monthly_spend"] for s in active)
            shares = [(s, attributed * s["monthly_spend"] / total_spend) for s in active]
            floored = [(s, int(share)) for s, share in shares]
            remainder = attributed - sum(n for _, n in floored)
            by_frac = sorted(shares, key=lambda t: t[1] - int(t[1]), reverse=True)
            bonus_ids = {s["id"] for s, _ in by_frac[:remainder]}
            for s, n in floored:
                conversions[s["id"]] += n + (1 if s["id"] in bonus_ids else 0)

        campaigns: list[Campaign] = []
        txns: list[Transaction] = []
        for s in specs:
            start = months[s["start_idx"]]
            end_month = months[s["start_idx"] + s["n_months"] - 1]
            conv = conversions[s["id"]]
            leads = conv * rng.randint(7, 14) + rng.randint(5, 30)
            campaigns.append(
                Campaign(
                    id=s["id"], name=s["name"], channel=s["channel"],
                    start_date=start, end_date=add_months(end_month, 1) - dt.timedelta(days=1),
                    spend=s["monthly_spend"] * s["n_months"], leads=leads, conversions=conv,
                )
            )
            for i in range(s["n_months"]):
                txns.append(
                    Transaction(
                        date=months[s["start_idx"] + i].replace(day=10),
                        type="expense", category="marketing", amount=s["monthly_spend"],
                        description=f"Campaign — {s['name']}", campaign_id=s["id"],
                    )
                )
        return campaigns, txns

    @staticmethod
    def _invoice_status(rng: random.Random, m_idx: int) -> str:
        if m_idx == N_MONTHS - 1:
            r = rng.random()
            return "paid" if r < 0.72 else ("issued" if r < 0.90 else "overdue")
        if m_idx == N_MONTHS - 2:
            return "paid" if rng.random() < 0.94 else "overdue"
        return "paid"

    @staticmethod
    def _gen_projects(rng: random.Random, months: list[dt.date], employees: list[Employee]) -> list[Project]:
        eng = [e for e in employees if e.department in ("Engineering", "Product")]
        rows = []
        for i, (name, status, desc) in enumerate(_PROJECTS, start=1):
            start = months[rng.randint(4, 12)]
            deadline = add_months(months[-1], rng.randint(-2, 4)).replace(day=28)
            if status == "completed":
                deadline = add_months(start, rng.randint(2, 4)).replace(day=28)
            rows.append(
                Project(id=i, name=name, status=status, owner_id=rng.choice(eng).id,
                        start_date=start, deadline=deadline, description=desc)
            )
        return rows

    @staticmethod
    def _gen_tasks(rng: random.Random, months: list[dt.date], employees: list[Employee]) -> list[Task]:
        by_dept: dict[str, list[Employee]] = {}
        for e in employees:
            by_dept.setdefault(e.department, []).append(e)
        rows = []
        for i, (title, dept, status, blocked_reason) in enumerate(_TASKS, start=1):
            assignee = rng.choice(by_dept.get(dept, employees))
            created = months[-rng.randint(1, 3)].replace(day=rng.randint(1, 28))
            due = None
            if status != "done":
                due = add_months(months[-1], rng.randint(1, 2)).replace(day=rng.randint(1, 28))
            rows.append(
                Task(id=i, title=title, department=dept, status=status,
                     assignee_id=assignee.id, due_date=due,
                     blocked_reason=blocked_reason, created_at=created)
            )
        return rows
