"""Per-table schema documentation, composed into per-agent schema docs.

Each specialist's sql_query tool gets ONLY the docs for its allowlisted tables —
least privilege applies to knowledge as well as access.
"""
from __future__ import annotations

TABLE_DOCS: dict[str, str] = {
    "transactions": """\
transactions(id, date, type, category, amount, description, customer_id, employee_id, campaign_id)
  type: 'revenue' | 'expense'; amount is always positive (sign comes from type).
  category: 'subscription' (all revenue) | 'salary' | 'cloud' | 'tools' | 'marketing' | 'office'.
  date is ISO 'YYYY-MM-DD'; group months with strftime('%Y-%m', date).""",
    "customers": """\
customers(id, name, plan, mrr, signup_date, churn_date)
  plan: 'starter' ($99) | 'growth' ($299) | 'scale' ($899); mrr = current monthly price.
  churn_date NULL means active today. Billing: one subscription transaction on the
  1st of each month from signup month until the month before churn_date.""",
    "invoices": """\
invoices(id, customer_id, transaction_id, amount, issue_date, due_date, status)
  status: 'paid' | 'issued' (sent, not yet due) | 'overdue'. One invoice per
  subscription transaction.""",
    "employees": """\
employees(id, name, role, department, salary_annual, hire_date)
  department: 'Leadership' | 'Engineering' | 'Product' | 'Marketing' |
  'Customer Success' | 'Operations'.""",
    "campaigns": """\
campaigns(id, name, channel, start_date, end_date, spend, leads, conversions)
  channel: e.g. 'Google Ads', 'LinkedIn', 'Content', 'X/Twitter', 'Webinar', 'Conference'.
  spend is the campaign's total; conversions = customers attributed to it.
  CAC per campaign/channel = spend / conversions.""",
    "projects": """\
projects(id, name, status, owner_id, start_date, deadline, description)
  status: 'planned' | 'active' | 'at_risk' | 'completed'. owner_id → employees.id.""",
    "tasks": """\
tasks(id, title, department, status, assignee_id, due_date, blocked_reason, created_at)
  status: 'open' | 'in_progress' | 'blocked' | 'done'. blocked_reason is set only
  when status = 'blocked'. assignee_id → employees.id.""",
    "meta": """\
meta(key, value)
  Dataset facts as strings: company, starting_cash, window_start, window_end
  (data coverage dates), months, generated_at.""",
}

FINANCE_TABLES = ["transactions", "customers", "invoices", "employees", "meta"]
MARKETING_TABLES = ["campaigns", "customers", "meta"]
ENGINEERING_TABLES = ["projects", "tasks", "employees", "meta"]
WORKFLOW_TABLES = ["tasks", "employees", "meta"]
# Finance sub-team (Phase 3)
REVENUE_TABLES = ["invoices", "customers", "meta"]
CONTROL_TABLES = ["transactions", "customers", "invoices", "employees", "campaigns", "meta"]


def build_schema_doc(tables: list[str]) -> str:
    return "\n".join(TABLE_DOCS[t] for t in tables)
