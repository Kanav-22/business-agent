"""ORM models for the Lumina Labs business database."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    """Every money movement. type: 'revenue' | 'expense'.

    category: 'subscription' (revenue) | 'salary' | 'cloud' | 'tools' | 'marketing' | 'office'.
    Nullable FKs tie a row back to the entity that explains it, which is what
    makes the dataset reconcilable.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    type: Mapped[str] = mapped_column(String(10), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(200))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)


class Customer(Base):
    """plan: 'starter' | 'growth' | 'scale'. mrr is the CURRENT monthly price.

    Billing convention: a customer is billed on the 1st of every month from their
    signup month through the month before churn_date (churn dates are always the
    1st of a month, meaning: no payment from that month on).
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    plan: Mapped[str] = mapped_column(String(10))
    mrr: Mapped[float] = mapped_column(Float)
    signup_date: Mapped[dt.date] = mapped_column(Date, index=True)
    churn_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True, index=True)


class Invoice(Base):
    """One invoice per subscription transaction. status: 'paid' | 'issued' | 'overdue'."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)
    amount: Mapped[float] = mapped_column(Float)
    issue_date: Mapped[dt.date] = mapped_column(Date, index=True)
    due_date: Mapped[dt.date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), index=True)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(30))
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date] = mapped_column(Date)
    spend: Mapped[float] = mapped_column(Float)
    leads: Mapped[int] = mapped_column(Integer)
    conversions: Mapped[int] = mapped_column(Integer)


class Project(Base):
    """status: 'planned' | 'active' | 'at_risk' | 'completed'."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(15))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    start_date: Mapped[dt.date] = mapped_column(Date)
    deadline: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(300))


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(60))
    department: Mapped[str] = mapped_column(String(30))
    salary_annual: Mapped[float] = mapped_column(Float)
    hire_date: Mapped[dt.date] = mapped_column(Date)


class Task(Base):
    """status: 'open' | 'in_progress' | 'blocked' | 'done'."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(15), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[dt.date] = mapped_column(Date)


class Meta(Base):
    """Key/value facts about the dataset (starting_cash, window bounds, seed…)."""

    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))


class Approval(Base):
    """Human-in-the-loop inbox. Outward-facing agent output (content drafts)
    lands here as 'pending' — nothing external happens without a click.

    status: 'pending' | 'approved' | 'rejected'.
    """

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # 'content'
    title: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(30))
    agent: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(10), index=True, default="pending")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)


class Report(Base):
    """Generated documents. kind: 'report' | 'briefing' | 'control_check'.

    Reports are artifacts, not source data — reseeding the synthetic dataset
    leaves them untouched.
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), index=True)
    agent: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    content: Mapped[str] = mapped_column(Text)
