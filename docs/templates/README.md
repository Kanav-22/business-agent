# Real business CSV templates

Copy these eight CSV files into one source directory, replace the example
rows with your data, then validate the directory before importing it. Files
must be UTF-8 CSV. Keep the canonical column names shown here: matching is
case-insensitive and column order does not matter, but missing or unknown
columns are rejected before any rows are processed.

Dates use ISO `YYYY-MM-DD`. Amounts and rates are plain positive numbers with
no currency symbols or thousands separators. Empty cells are allowed only for
columns explicitly marked optional below. Names used as foreign keys are
trimmed and matched case-insensitively; spaces and punctuation must otherwise
match. Names that differ only by case are rejected as duplicates.

## Required files

`transactions.csv`, `customers.csv`, and `meta.csv` are required. The importer
will not write anything when a required file is missing or any file has a
validation error.

### `transactions.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `date` | yes | Posting date in ISO format. |
| `type` | yes | `revenue` or `expense`. |
| `category` | yes | `subscription`, `salary`, `cloud`, `tools`, `marketing`, or `office`. `subscription` is revenue; the other categories are expenses. |
| `amount` | yes | Positive transaction amount. |
| `description` | yes | Human-readable explanation of the movement. |
| `customer_name` | no | Exact `customers.csv` name. Use on customer-linked revenue such as subscriptions. |
| `employee_name` | no | Exact `employees.csv` name. Use on employee-linked salary expenses. |
| `campaign_name` | no | Exact `campaigns.csv` name. Use on campaign-linked marketing expenses. |

### `customers.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Unique customer name used by transaction and invoice foreign keys. |
| `plan` | yes | `starter`, `growth`, or `scale`. |
| `mrr` | yes | Positive current monthly recurring revenue for the customer. |
| `signup_date` | yes | Signup date in ISO format. |
| `churn_date` | no | Churn date in ISO format; it must not precede `signup_date`. Leave empty for an active customer. |

### `meta.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `key` | yes | Metadata key. A `starting_cash` row is required. Other business facts, such as `company`, may be added as rows. |
| `value` | yes | Metadata value. `starting_cash` must be a positive number. |

Do not add `window_start`, `window_end`, `generated_at`, or `provider`
yourself. The importer owns those keys: it computes the window bounds from
your data and stamps the provider and generation time only after validation.

## Optional files

The remaining files are optional. Omitting one imports an empty table and
produces a warning: no invoices removes Revenue-agent invoice grounding; no
campaigns removes CMO campaign grounding; no projects removes CTO delivery
grounding; no employees removes CFO payroll and ownership grounding; and no
tasks removes Coordinator task and blocker grounding.

### `invoices.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `customer_name` | yes | Exact `customers.csv` name. |
| `amount` | yes | Positive invoice amount. |
| `issue_date` | yes | Issue date in ISO format. |
| `due_date` | yes | Due date in ISO format; it must be on or after `issue_date`. |
| `status` | yes | `paid`, `issued`, or `overdue`. |

Each invoice must match exactly one subscription-revenue transaction using
the same customer name and issue/posting date, with an amount difference of
at most `0.01`. Zero matches or more than one match is an error; the importer
never guesses which transaction to link.

### `campaigns.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Campaign name used by transaction foreign keys. |
| `channel` | yes | Acquisition channel, such as `Google Ads` or `Webinar`; free text. |
| `start_date` | yes | Start date in ISO format. |
| `end_date` | yes | End date in ISO format; it must be on or after `start_date`. |
| `spend` | yes | Positive total campaign spend. |
| `leads` | yes | Non-negative whole-number lead count. |
| `conversions` | yes | Non-negative whole-number conversion count, no greater than `leads`. |

For a reconciling dataset, marketing transactions linked through
`campaign_name` should total each campaign's `spend`.

### `projects.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Project name. |
| `status` | yes | `planned`, `active`, `at_risk`, or `completed`. |
| `owner_name` | no | Exact `employees.csv` name. |
| `start_date` | yes | Start date in ISO format. |
| `deadline` | no | Deadline in ISO format; when present, it must not precede `start_date`. |
| `description` | yes | Short project scope or outcome. |

### `employees.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Employee name used by transaction, project, and task foreign keys. |
| `role` | yes | Job title; free text. |
| `department` | yes | Department name; free text. |
| `salary_annual` | yes | Positive annual salary. |
| `hire_date` | yes | Hire date in ISO format. |

For a reconciling dataset, each employee's monthly salary transactions should
equal `salary_annual / 12` within normal cent rounding.

### `tasks.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `title` | yes | Task title. |
| `department` | yes | Owning department; free text. |
| `status` | yes | `open`, `in_progress`, `blocked`, or `done`. |
| `assignee_name` | no | Exact `employees.csv` name. |
| `due_date` | no | Due date in ISO format; when present, it must not precede `created_at`. |
| `blocked_reason` | no | Why progress is blocked. Provide it for blocked tasks; otherwise leave it empty. |
| `created_at` | yes | Creation date in ISO format. |

## Validate and import safely

From `backend/`, run:

```bash
python3 scripts/import_real.py --source ../docs/templates --check
python3 scripts/import_real.py --source ../docs/templates --db data/business.db
```

`--check` performs full structural validation and prints a reconciliation
preview without writing to the database. Reconciliation `[WARN]` lines flag
books that do not balance but do not block import; structural row errors do.
The small examples intentionally omit payroll and campaign-spend transactions,
so their reconciliation preview can warn after the CSV structure validates.

Importing into a database that already contains business data is refused.
Use `--force` only when you deliberately want to replace the business tables:

```bash
python3 scripts/import_real.py --source ../docs/templates --db data/business.db --force
```

`--force` never deletes artifact tables such as reports, memories, ideas,
approvals, founder or business profiles, and evaluation results. Always run
`--check` first and keep a backup of the target database before replacing
business data.
