"""Validate or import canonical real-business CSV exports.

Usage, from backend/:
    python scripts/import_real.py --source <dir> [--db <path>] [--check] [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.data.real import RealBusinessProvider  # noqa: E402
from app.db import make_engine  # noqa: E402


def _print_summary(summary: dict, *, checked: bool, db_path: Path | None) -> None:
    if checked:
        print("CSV validation passed; no database changes were made.")
    else:
        print(f"Imported real business data into {db_path}:")
    for table, count in summary["tables"].items():
        print(f"  {table:<14} {count:>6} rows")
    print(f"  {'window':<14} {summary['window'][0]} -> {summary['window'][1]}")

    if summary["warnings"]:
        print("\nGrounding warnings:")
        for warning in summary["warnings"]:
            print(f"  {warning}")

    reconciliation = summary.get("reconciliation", [])
    if reconciliation:
        print("\nReconciliation preview:")
        for line in reconciliation:
            print(f"  {line}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Directory containing the canonical CSV files",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Target SQLite path (default: BUSINESS_AGENT_DB or standard path)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and preview reconciliation without opening the database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing business rows while preserving artifacts",
    )
    args = parser.parse_args(argv)

    provider = RealBusinessProvider(args.source)
    try:
        if args.check:
            summary = provider.check()
            _print_summary(summary, checked=True, db_path=None)
        else:
            db_path = args.db or Settings.from_env().db_path
            summary = provider.provision(make_engine(db_path), force=args.force)
            _print_summary(summary, checked=False, db_path=db_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
