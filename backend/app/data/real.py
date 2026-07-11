"""Validated CSV provider for real business exports.

The importer deliberately separates parsing from persistence. Every file is
decoded, structurally checked, converted, cross-referenced, and reconciled in
memory before a database transaction begins. A failed import therefore leaves
both the prior business dataset and all long-lived artifacts untouched.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import delete, func, select
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


CANONICAL_HEADERS: dict[str, tuple[str, ...]] = {
    "transactions.csv": (
        "date",
        "type",
        "category",
        "amount",
        "description",
        "customer_name",
        "employee_name",
        "campaign_name",
    ),
    "customers.csv": ("name", "plan", "mrr", "signup_date", "churn_date"),
    "meta.csv": ("key", "value"),
    "invoices.csv": (
        "customer_name",
        "amount",
        "issue_date",
        "due_date",
        "status",
    ),
    "campaigns.csv": (
        "name",
        "channel",
        "start_date",
        "end_date",
        "spend",
        "leads",
        "conversions",
    ),
    "projects.csv": (
        "name",
        "status",
        "owner_name",
        "start_date",
        "deadline",
        "description",
    ),
    "employees.csv": (
        "name",
        "role",
        "department",
        "salary_annual",
        "hire_date",
    ),
    "tasks.csv": (
        "title",
        "department",
        "status",
        "assignee_name",
        "due_date",
        "blocked_reason",
        "created_at",
    ),
}

REQUIRED_FILES = frozenset({"transactions.csv", "customers.csv", "meta.csv"})

_OPTIONAL_WARNINGS = {
    "invoices.csv": "[WARN] invoices.csv is absent; the Revenue agent loses invoice grounding.",
    "campaigns.csv": "[WARN] campaigns.csv is absent; the CMO and Control agent lose campaign grounding.",
    "projects.csv": "[WARN] projects.csv is absent; the CTO loses project grounding.",
    "employees.csv": "[WARN] employees.csv is absent; the CFO, COO, and Coordinator lose payroll and staffing grounding.",
    "tasks.csv": "[WARN] tasks.csv is absent; the Coordinator and CTO lose task grounding.",
}

_TRANSACTION_TYPES = frozenset({"revenue", "expense"})
_TRANSACTION_CATEGORIES = frozenset(
    {"subscription", "salary", "cloud", "tools", "marketing", "office"}
)
_PLANS = frozenset({"starter", "growth", "scale"})
_INVOICE_STATUSES = frozenset({"paid", "issued", "overdue"})
_PROJECT_STATUSES = frozenset({"planned", "active", "at_risk", "completed"})
_TASK_STATUSES = frozenset({"open", "in_progress", "blocked", "done"})
_COMPUTED_META_KEYS = frozenset(
    {"generated_at", "provider", "window_start", "window_end"}
)
_CENT = Decimal("0.01")

_BUSINESS_MODELS = (Invoice, Transaction, Task, Project, Campaign, Customer, Employee, Meta)
_DELETE_ORDER = _BUSINESS_MODELS


class RealDataValidationError(ValueError):
    """A bounded collection of source errors safe to show directly in a CLI."""

    def __init__(self, errors: list[str]):
        self.errors = errors[:20]
        super().__init__("CSV validation failed:\n" + "\n".join(self.errors))


@dataclass
class _Validation:
    errors: list[str] = field(default_factory=list)
    count: int = 0

    def add(self, filename: str, line: int, message: str) -> None:
        self.count += 1
        if len(self.errors) < 20:
            self.errors.append(f"{filename}:{line}: {message}")

    def raise_if_any(self) -> None:
        if self.count:
            raise RealDataValidationError(self.errors)


@dataclass
class _PreparedData:
    customers: list[Customer]
    employees: list[Employee]
    campaigns: list[Campaign]
    transactions: list[Transaction]
    invoices: list[Invoice]
    projects: list[Project]
    tasks: list[Task]
    meta: list[Meta]
    window_start: dt.date
    window_end: dt.date
    warnings: list[str]
    customer_mrr: dict[int, Decimal]
    employee_salary: dict[int, Decimal]
    campaign_spend: dict[int, Decimal]
    transaction_amount: dict[int, Decimal]

    def table_counts(self) -> dict[str, int]:
        return {
            "customers": len(self.customers),
            "employees": len(self.employees),
            "campaigns": len(self.campaigns),
            "transactions": len(self.transactions),
            "invoices": len(self.invoices),
            "projects": len(self.projects),
            "tasks": len(self.tasks),
            "meta": len(self.meta),
        }

    def summary(self) -> dict:
        return {
            "tables": self.table_counts(),
            "window": [self.window_start.isoformat(), self.window_end.isoformat()],
            "warnings": list(self.warnings),
        }


class RealBusinessProvider(DataProvider):
    """Import one directory of canonical CSV exports into the business schema."""

    name = "real"

    def __init__(self, source_dir: Path):
        self.source_dir = Path(source_dir)

    def provision(self, engine: Engine, *, force: bool = False) -> dict:
        prepared = self._prepare()
        Base.metadata.create_all(engine)
        if not force and self._has_business_rows(engine):
            raise ValueError(
                "target database already contains business data; use force=True to replace it"
            )

        with Session(engine) as session:
            for model in _DELETE_ORDER:
                session.execute(delete(model))
            session.add_all(prepared.customers)
            session.add_all(prepared.employees)
            session.add_all(prepared.campaigns)
            session.add_all(prepared.transactions)
            session.add_all(prepared.invoices)
            session.add_all(prepared.projects)
            session.add_all(prepared.tasks)
            session.add_all(prepared.meta)
            session.commit()
        return prepared.summary()

    def check(self, engine: Engine | None = None) -> dict:
        """Validate and reconcile entirely in memory; ``engine`` is never touched."""
        del engine
        prepared = self._prepare()
        summary = prepared.summary()
        summary["reconciliation"] = self._reconcile(prepared)
        return summary

    @staticmethod
    def _has_business_rows(engine: Engine) -> bool:
        with Session(engine) as session:
            return any(
                (session.scalar(select(func.count()).select_from(model)) or 0) > 0
                for model in _BUSINESS_MODELS
            )

    def _prepare(self) -> _PreparedData:
        validation = _Validation()
        raw_tables, warnings = self._load_tables(validation)

        customers, customer_names, customer_mrr = self._parse_customers(
            raw_tables["customers.csv"], validation
        )
        employees, employee_names, employee_salary = self._parse_employees(
            raw_tables["employees.csv"], validation
        )
        campaigns, campaign_names, campaign_spend = self._parse_campaigns(
            raw_tables["campaigns.csv"], validation
        )
        transactions, transaction_amount = self._parse_transactions(
            raw_tables["transactions.csv"],
            validation,
            customer_names,
            employee_names,
            campaign_names,
        )
        invoices = self._parse_invoices(
            raw_tables["invoices.csv"],
            validation,
            customer_names,
            transactions,
            transaction_amount,
        )
        projects = self._parse_projects(
            raw_tables["projects.csv"], validation, employee_names
        )
        tasks = self._parse_tasks(
            raw_tables["tasks.csv"], validation, employee_names
        )
        user_meta = self._parse_meta(raw_tables["meta.csv"], validation)

        if not transactions:
            validation.add("transactions.csv", 0, "at least one valid transaction is required")
        validation.raise_if_any()

        window_start = min(row.date for row in transactions)
        window_end = max(row.date for row in transactions)
        generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
        computed_meta = {
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "generated_at": generated_at,
            "provider": self.name,
        }
        merged_meta = {
            key: value
            for key, value in user_meta.items()
            if key not in _COMPUTED_META_KEYS
        }
        merged_meta.update(computed_meta)
        meta_rows = [Meta(key=key, value=value) for key, value in merged_meta.items()]

        return _PreparedData(
            customers=customers,
            employees=employees,
            campaigns=campaigns,
            transactions=transactions,
            invoices=invoices,
            projects=projects,
            tasks=tasks,
            meta=meta_rows,
            window_start=window_start,
            window_end=window_end,
            warnings=warnings,
            customer_mrr=customer_mrr,
            employee_salary=employee_salary,
            campaign_spend=campaign_spend,
            transaction_amount=transaction_amount,
        )

    def _load_tables(
        self, validation: _Validation
    ) -> tuple[dict[str, list[dict]], list[str]]:
        if not self.source_dir.is_dir():
            validation.add(
                "source",
                0,
                f"directory does not exist or is not a directory: {self.source_dir}",
            )
            validation.raise_if_any()

        tables: dict[str, list[dict]] = {}
        warnings: list[str] = []
        for filename, headers in CANONICAL_HEADERS.items():
            path = self.source_dir / filename
            if not path.is_file():
                tables[filename] = []
                if filename in REQUIRED_FILES:
                    validation.add(filename, 0, "required file is missing")
                else:
                    warnings.append(_OPTIONAL_WARNINGS[filename])
                continue
            tables[filename] = self._read_csv(
                path,
                headers,
                validation,
                require_rows=filename in REQUIRED_FILES,
            )
        return tables, warnings

    @staticmethod
    def _read_csv(
        path: Path,
        headers: tuple[str, ...],
        validation: _Validation,
        *,
        require_rows: bool,
    ) -> list[dict]:
        filename = path.name
        rows: list[dict] = []
        reader = None
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, strict=True)
                try:
                    source_headers = next(reader)
                except StopIteration:
                    validation.add(filename, 0, "file is empty")
                    return []
                if not source_headers or not any(value.strip() for value in source_headers):
                    validation.add(filename, 0, "file is empty")
                    return []

                normalized = [value.strip().lower() for value in source_headers]
                duplicates = sorted(
                    {name for name in normalized if normalized.count(name) > 1}
                )
                expected = set(headers)
                actual = set(normalized)
                if duplicates:
                    validation.add(
                        filename,
                        1,
                        f"duplicate headers: {', '.join(duplicates)}",
                    )
                missing = sorted(expected - actual)
                unknown = sorted(actual - expected)
                if missing:
                    validation.add(
                        filename,
                        1,
                        f"missing headers: {', '.join(missing)}",
                    )
                if unknown:
                    validation.add(
                        filename,
                        1,
                        f"unknown headers: {', '.join(unknown)}",
                    )
                if duplicates or missing or unknown or len(normalized) != len(headers):
                    return []

                for values in reader:
                    line = reader.line_num
                    if not any(value.strip() for value in values):
                        continue
                    if len(values) != len(normalized):
                        validation.add(
                            filename,
                            line,
                            f"expected {len(normalized)} columns, found {len(values)}",
                        )
                        continue
                    row = dict(zip(normalized, values))
                    row["_line"] = line
                    rows.append(row)
        except UnicodeDecodeError:
            validation.add(filename, 0, "file is not valid UTF-8")
            return []
        except csv.Error as exc:
            line = reader.line_num if reader is not None else 0
            validation.add(filename, line, f"invalid CSV: {exc}")
            return []
        except OSError as exc:
            validation.add(filename, 0, f"could not read file: {exc}")
            return []

        if require_rows and not rows:
            validation.add(filename, 0, "file must contain at least one data row")
        return rows

    @staticmethod
    def _line(row: dict) -> int:
        return int(row["_line"])

    @staticmethod
    def _text(
        row: dict,
        field_name: str,
        filename: str,
        validation: _Validation,
        *,
        maximum: int,
        required: bool = True,
    ) -> str | None:
        value = str(row.get(field_name, "") or "").strip()
        if not value:
            if required:
                validation.add(
                    filename,
                    RealBusinessProvider._line(row),
                    f"{field_name} is required",
                )
            return None
        if len(value) > maximum:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be at most {maximum} characters",
            )
            return None
        return value

    @staticmethod
    def _enum(
        row: dict,
        field_name: str,
        filename: str,
        validation: _Validation,
        allowed: frozenset[str],
    ) -> str | None:
        value = RealBusinessProvider._text(
            row,
            field_name,
            filename,
            validation,
            maximum=40,
        )
        if value is None:
            return None
        normalized = value.lower()
        if normalized not in allowed:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} value {value!r} must be one of: {', '.join(sorted(allowed))}",
            )
            return None
        return normalized

    @staticmethod
    def _date(
        row: dict,
        field_name: str,
        filename: str,
        validation: _Validation,
        *,
        required: bool = True,
    ) -> dt.date | None:
        value = str(row.get(field_name, "") or "").strip()
        if not value:
            if required:
                validation.add(
                    filename,
                    RealBusinessProvider._line(row),
                    f"{field_name} is required",
                )
            return None
        try:
            parsed = dt.date.fromisoformat(value)
        except ValueError:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be an ISO date (YYYY-MM-DD)",
            )
            return None
        if parsed.isoformat() != value:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must use YYYY-MM-DD format",
            )
            return None
        return parsed

    @staticmethod
    def _decimal(
        row: dict,
        field_name: str,
        filename: str,
        validation: _Validation,
        *,
        positive: bool = True,
    ) -> Decimal | None:
        value = str(row.get(field_name, "") or "").strip()
        if not value:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} is required",
            )
            return None
        if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value):
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be a plain decimal number without separators or exponents",
            )
            return None
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            parsed = Decimal("NaN")
        try:
            finite_as_float = math.isfinite(float(parsed))
        except (OverflowError, ValueError):
            finite_as_float = False
        if not parsed.is_finite() or not finite_as_float:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be a finite number",
            )
            return None
        if positive and (parsed <= 0 or float(parsed) <= 0):
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be greater than zero",
            )
            return None
        return parsed

    @staticmethod
    def _integer(
        row: dict,
        field_name: str,
        filename: str,
        validation: _Validation,
    ) -> int | None:
        value = str(row.get(field_name, "") or "").strip()
        try:
            parsed = int(value)
        except ValueError:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be a non-negative integer",
            )
            return None
        if parsed < 0:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} must be a non-negative integer",
            )
            return None
        return parsed

    @staticmethod
    def _register_name(
        name: str | None,
        entity_id: int,
        names: dict[str, int],
        filename: str,
        line: int,
        validation: _Validation,
    ) -> bool:
        if name is None:
            return False
        key = name.casefold()
        if key in names:
            validation.add(filename, line, f"duplicate name: {name}")
            return False
        names[key] = entity_id
        return True

    @staticmethod
    def _resolve_name(
        row: dict,
        field_name: str,
        filename: str,
        validation: _Validation,
        names: dict[str, int],
        *,
        maximum: int,
        required: bool = False,
    ) -> int | None:
        value = RealBusinessProvider._text(
            row,
            field_name,
            filename,
            validation,
            maximum=maximum,
            required=required,
        )
        if value is None:
            return None
        resolved = names.get(value.casefold())
        if resolved is None:
            validation.add(
                filename,
                RealBusinessProvider._line(row),
                f"{field_name} does not match an imported name: {value}",
            )
        return resolved

    def _parse_customers(
        self, rows: list[dict], validation: _Validation
    ) -> tuple[list[Customer], dict[str, int], dict[int, Decimal]]:
        filename = "customers.csv"
        customers: list[Customer] = []
        names: dict[str, int] = {}
        mrr_by_id: dict[int, Decimal] = {}
        for row in rows:
            before = validation.count
            name = self._text(row, "name", filename, validation, maximum=80)
            plan = self._enum(row, "plan", filename, validation, _PLANS)
            mrr = self._decimal(row, "mrr", filename, validation)
            signup = self._date(row, "signup_date", filename, validation)
            churn = self._date(
                row,
                "churn_date",
                filename,
                validation,
                required=False,
            )
            entity_id = len(customers) + 1
            registered = self._register_name(
                name,
                entity_id,
                names,
                filename,
                self._line(row),
                validation,
            )
            if signup and churn and churn < signup:
                validation.add(
                    filename,
                    self._line(row),
                    "churn_date cannot be before signup_date",
                )
            if validation.count == before and registered:
                customer = Customer(
                    id=entity_id,
                    name=name,
                    plan=plan,
                    mrr=float(mrr),
                    signup_date=signup,
                    churn_date=churn,
                )
                customers.append(customer)
                mrr_by_id[entity_id] = mrr
        return customers, names, mrr_by_id

    def _parse_employees(
        self, rows: list[dict], validation: _Validation
    ) -> tuple[list[Employee], dict[str, int], dict[int, Decimal]]:
        filename = "employees.csv"
        employees: list[Employee] = []
        names: dict[str, int] = {}
        salaries: dict[int, Decimal] = {}
        for row in rows:
            before = validation.count
            name = self._text(row, "name", filename, validation, maximum=80)
            role = self._text(row, "role", filename, validation, maximum=60)
            department = self._text(
                row, "department", filename, validation, maximum=30
            )
            salary = self._decimal(
                row, "salary_annual", filename, validation
            )
            hire_date = self._date(row, "hire_date", filename, validation)
            entity_id = len(employees) + 1
            registered = self._register_name(
                name,
                entity_id,
                names,
                filename,
                self._line(row),
                validation,
            )
            if validation.count == before and registered:
                employees.append(
                    Employee(
                        id=entity_id,
                        name=name,
                        role=role,
                        department=department,
                        salary_annual=float(salary),
                        hire_date=hire_date,
                    )
                )
                salaries[entity_id] = salary
        return employees, names, salaries

    def _parse_campaigns(
        self, rows: list[dict], validation: _Validation
    ) -> tuple[list[Campaign], dict[str, int], dict[int, Decimal]]:
        filename = "campaigns.csv"
        campaigns: list[Campaign] = []
        names: dict[str, int] = {}
        spend_by_id: dict[int, Decimal] = {}
        for row in rows:
            before = validation.count
            name = self._text(row, "name", filename, validation, maximum=120)
            channel = self._text(row, "channel", filename, validation, maximum=30)
            start_date = self._date(row, "start_date", filename, validation)
            end_date = self._date(row, "end_date", filename, validation)
            spend = self._decimal(row, "spend", filename, validation)
            leads = self._integer(row, "leads", filename, validation)
            conversions = self._integer(row, "conversions", filename, validation)
            entity_id = len(campaigns) + 1
            registered = self._register_name(
                name,
                entity_id,
                names,
                filename,
                self._line(row),
                validation,
            )
            if start_date and end_date and end_date < start_date:
                validation.add(
                    filename,
                    self._line(row),
                    "end_date cannot be before start_date",
                )
            if leads is not None and conversions is not None and conversions > leads:
                validation.add(
                    filename,
                    self._line(row),
                    "conversions cannot exceed leads",
                )
            if validation.count == before and registered:
                campaigns.append(
                    Campaign(
                        id=entity_id,
                        name=name,
                        channel=channel,
                        start_date=start_date,
                        end_date=end_date,
                        spend=float(spend),
                        leads=leads,
                        conversions=conversions,
                    )
                )
                spend_by_id[entity_id] = spend
        return campaigns, names, spend_by_id

    def _parse_transactions(
        self,
        rows: list[dict],
        validation: _Validation,
        customer_names: dict[str, int],
        employee_names: dict[str, int],
        campaign_names: dict[str, int],
    ) -> tuple[list[Transaction], dict[int, Decimal]]:
        filename = "transactions.csv"
        transactions: list[Transaction] = []
        amounts: dict[int, Decimal] = {}
        for row in rows:
            before = validation.count
            date = self._date(row, "date", filename, validation)
            txn_type = self._enum(
                row, "type", filename, validation, _TRANSACTION_TYPES
            )
            category = self._enum(
                row,
                "category",
                filename,
                validation,
                _TRANSACTION_CATEGORIES,
            )
            amount = self._decimal(row, "amount", filename, validation)
            description = self._text(
                row, "description", filename, validation, maximum=200
            )
            customer_id = self._resolve_name(
                row,
                "customer_name",
                filename,
                validation,
                customer_names,
                maximum=80,
            )
            employee_id = self._resolve_name(
                row,
                "employee_name",
                filename,
                validation,
                employee_names,
                maximum=80,
            )
            campaign_id = self._resolve_name(
                row,
                "campaign_name",
                filename,
                validation,
                campaign_names,
                maximum=120,
            )
            if txn_type == "revenue" and category != "subscription":
                validation.add(
                    filename,
                    self._line(row),
                    "revenue transactions must use category subscription",
                )
            if txn_type == "expense" and category == "subscription":
                validation.add(
                    filename,
                    self._line(row),
                    "expense transactions cannot use category subscription",
                )
            entity_id = len(transactions) + 1
            if validation.count == before:
                transactions.append(
                    Transaction(
                        id=entity_id,
                        date=date,
                        type=txn_type,
                        category=category,
                        amount=float(amount),
                        description=description,
                        customer_id=customer_id,
                        employee_id=employee_id,
                        campaign_id=campaign_id,
                    )
                )
                amounts[entity_id] = amount
        return transactions, amounts

    def _parse_invoices(
        self,
        rows: list[dict],
        validation: _Validation,
        customer_names: dict[str, int],
        transactions: list[Transaction],
        transaction_amounts: dict[int, Decimal],
    ) -> list[Invoice]:
        filename = "invoices.csv"
        invoices: list[Invoice] = []
        claimed_transactions: set[int] = set()
        for row in rows:
            before = validation.count
            customer_id = self._resolve_name(
                row,
                "customer_name",
                filename,
                validation,
                customer_names,
                maximum=80,
                required=True,
            )
            amount = self._decimal(row, "amount", filename, validation)
            issue_date = self._date(row, "issue_date", filename, validation)
            due_date = self._date(row, "due_date", filename, validation)
            status = self._enum(
                row, "status", filename, validation, _INVOICE_STATUSES
            )
            if issue_date and due_date and due_date < issue_date:
                validation.add(
                    filename,
                    self._line(row),
                    "due_date cannot be before issue_date",
                )
            if validation.count != before:
                continue

            candidates = [
                transaction
                for transaction in transactions
                if transaction.type == "revenue"
                and transaction.customer_id == customer_id
                and transaction.date == issue_date
                and abs(transaction_amounts[transaction.id] - amount) <= _CENT
            ]
            if not candidates:
                validation.add(
                    filename,
                    self._line(row),
                    "unmatched invoice: no matching revenue transaction by customer, amount, and issue_date",
                )
                continue
            if len(candidates) > 1:
                validation.add(
                    filename,
                    self._line(row),
                    "invoice matches multiple revenue transactions; refusing to guess",
                )
                continue
            transaction_id = candidates[0].id
            if transaction_id in claimed_transactions:
                validation.add(
                    filename,
                    self._line(row),
                    "revenue transaction is already matched to another invoice",
                )
                continue
            claimed_transactions.add(transaction_id)
            invoices.append(
                Invoice(
                    id=len(invoices) + 1,
                    customer_id=customer_id,
                    transaction_id=transaction_id,
                    amount=float(amount),
                    issue_date=issue_date,
                    due_date=due_date,
                    status=status,
                )
            )
        return invoices

    def _parse_projects(
        self,
        rows: list[dict],
        validation: _Validation,
        employee_names: dict[str, int],
    ) -> list[Project]:
        filename = "projects.csv"
        projects: list[Project] = []
        for row in rows:
            before = validation.count
            name = self._text(row, "name", filename, validation, maximum=120)
            status = self._enum(
                row, "status", filename, validation, _PROJECT_STATUSES
            )
            owner_id = self._resolve_name(
                row,
                "owner_name",
                filename,
                validation,
                employee_names,
                maximum=80,
            )
            start_date = self._date(row, "start_date", filename, validation)
            deadline = self._date(
                row, "deadline", filename, validation, required=False
            )
            description = self._text(
                row, "description", filename, validation, maximum=300
            )
            if start_date and deadline and deadline < start_date:
                validation.add(
                    filename,
                    self._line(row),
                    "deadline cannot be before start_date",
                )
            if validation.count == before:
                projects.append(
                    Project(
                        id=len(projects) + 1,
                        name=name,
                        status=status,
                        owner_id=owner_id,
                        start_date=start_date,
                        deadline=deadline,
                        description=description,
                    )
                )
        return projects

    def _parse_tasks(
        self,
        rows: list[dict],
        validation: _Validation,
        employee_names: dict[str, int],
    ) -> list[Task]:
        filename = "tasks.csv"
        tasks: list[Task] = []
        for row in rows:
            before = validation.count
            title = self._text(row, "title", filename, validation, maximum=200)
            department = self._text(
                row, "department", filename, validation, maximum=30
            )
            status = self._enum(
                row, "status", filename, validation, _TASK_STATUSES
            )
            assignee_id = self._resolve_name(
                row,
                "assignee_name",
                filename,
                validation,
                employee_names,
                maximum=80,
            )
            due_date = self._date(
                row, "due_date", filename, validation, required=False
            )
            blocked_reason = self._text(
                row,
                "blocked_reason",
                filename,
                validation,
                maximum=200,
                required=False,
            )
            created_at = self._date(row, "created_at", filename, validation)
            if created_at and due_date and due_date < created_at:
                validation.add(
                    filename,
                    self._line(row),
                    "due_date cannot be before created_at",
                )
            if validation.count == before:
                tasks.append(
                    Task(
                        id=len(tasks) + 1,
                        title=title,
                        department=department,
                        status=status,
                        assignee_id=assignee_id,
                        due_date=due_date,
                        blocked_reason=blocked_reason,
                        created_at=created_at,
                    )
                )
        return tasks

    def _parse_meta(
        self, rows: list[dict], validation: _Validation
    ) -> dict[str, str]:
        filename = "meta.csv"
        values: dict[str, str] = {}
        starting_cash_line: int | None = None
        for row in rows:
            before = validation.count
            key = self._text(row, "key", filename, validation, maximum=40)
            value = self._text(row, "value", filename, validation, maximum=200)
            normalized = key.lower() if key else None
            if normalized and normalized in values:
                validation.add(
                    filename,
                    self._line(row),
                    f"duplicate meta key: {normalized}",
                )
            if normalized == "starting_cash":
                starting_cash_line = self._line(row)
                self._decimal(row, "value", filename, validation)
            if validation.count == before:
                values[normalized] = value
        if "starting_cash" not in values:
            validation.add(
                filename,
                starting_cash_line or 0,
                "starting_cash meta key is required and must be valid",
            )
        return values

    @staticmethod
    def _month_floor(value: dt.date) -> dt.date:
        return value.replace(day=1)

    @staticmethod
    def _add_month(value: dt.date) -> dt.date:
        year, month = divmod(value.year * 12 + value.month, 12)
        return dt.date(year, month + 1, 1)

    def _reconcile(self, prepared: _PreparedData) -> list[str]:
        lines: list[str] = []
        month = self._month_floor(prepared.window_start)
        last_month = self._month_floor(prepared.window_end)
        while month <= last_month:
            next_month = self._add_month(month)
            billed = sum(
                prepared.transaction_amount[transaction.id]
                for transaction in prepared.transactions
                if transaction.type == "revenue"
                and transaction.category == "subscription"
                and month <= transaction.date < next_month
            )
            expected_mrr = sum(
                prepared.customer_mrr[customer.id]
                for customer in prepared.customers
                if self._month_floor(customer.signup_date) <= month
                and (
                    customer.churn_date is None
                    or self._month_floor(customer.churn_date) > month
                )
            )
            lines.append(
                self._reconciliation_line(
                    f"{month:%Y-%m} subscription revenue",
                    billed,
                    expected_mrr,
                )
            )

            if prepared.employees:
                payroll = sum(
                    prepared.transaction_amount[transaction.id]
                    for transaction in prepared.transactions
                    if transaction.type == "expense"
                    and transaction.category == "salary"
                    and month <= transaction.date < next_month
                )
                expected_payroll = sum(
                    (prepared.employee_salary[employee.id] / Decimal(12)).quantize(_CENT)
                    for employee in prepared.employees
                    if self._month_floor(employee.hire_date) <= month
                )
                lines.append(
                    self._reconciliation_line(
                        f"{month:%Y-%m} payroll",
                        payroll,
                        expected_payroll,
                    )
                )
            month = next_month

        if not prepared.employees:
            lines.append(
                "[WARN] payroll reconciliation unavailable because employees.csv is absent"
            )

        if prepared.campaigns:
            for campaign in prepared.campaigns:
                actual_spend = sum(
                    prepared.transaction_amount[transaction.id]
                    for transaction in prepared.transactions
                    if transaction.type == "expense"
                    and transaction.category == "marketing"
                    and transaction.campaign_id == campaign.id
                )
                lines.append(
                    self._reconciliation_line(
                        f"campaign {campaign.name}",
                        actual_spend,
                        prepared.campaign_spend[campaign.id],
                    )
                )
        else:
            lines.append(
                "[WARN] campaign reconciliation unavailable because campaigns.csv is absent"
            )

        unlinked_marketing = [
            transaction
            for transaction in prepared.transactions
            if transaction.type == "expense"
            and transaction.category == "marketing"
            and transaction.campaign_id is None
        ]
        if unlinked_marketing:
            amount = sum(
                prepared.transaction_amount[transaction.id]
                for transaction in unlinked_marketing
            )
            lines.append(
                f"[WARN] unlinked marketing transactions: "
                f"count={len(unlinked_marketing)}, amount={amount:.2f}"
            )
        else:
            lines.append("[OK] marketing transactions: all rows are linked to campaigns")
        return lines

    @staticmethod
    def _reconciliation_line(label: str, actual: Decimal, expected: Decimal) -> str:
        status = "OK" if abs(actual - expected) <= _CENT else "WARN"
        return (
            f"[{status}] {label}: transactions={actual:.2f}, "
            f"expected={expected:.2f}"
        )
