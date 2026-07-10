"""Seed (or re-seed) the Lumina Labs synthetic database.

Usage, from backend/:
    python scripts/seed.py [--seed 7] [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.kpis import get_kpis  # noqa: E402
from app.config import Settings  # noqa: E402
from app.data.synthetic import SyntheticProvider  # noqa: E402
from app.db import make_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (default: settings)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if data exists")
    args = parser.parse_args()

    settings = Settings.from_env()
    seed = args.seed if args.seed is not None else settings.data_seed
    engine = make_engine(settings.db_path)

    summary = SyntheticProvider(seed=seed).provision(engine, force=args.force)
    if summary.get("skipped"):
        print(f"Database already provisioned at {settings.db_path} (use --force to regenerate).")
    else:
        print(f"Seeded {settings.db_path}:")
        for table, count in summary.items():
            if table != "skipped":
                print(f"  {table:<14} {count:>6} rows")

    kpis = get_kpis(engine)
    print("\nHeadline numbers:")
    print(f"  Company            {kpis['company']}")
    print(f"  Data window        {kpis['window_start']} → {kpis['window_end']}")
    print(f"  MRR                ${kpis['mrr']:,.0f}")
    print(f"  Active customers   {kpis['active_customers']}")
    print(f"  Cash               ${kpis['cash']:,.0f}")
    print(f"  Avg monthly burn   ${kpis['avg_monthly_burn']:,.0f}")
    runway = kpis["runway_months"]
    print(f"  Runway             {runway} months" if runway else "  Runway             ∞")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
