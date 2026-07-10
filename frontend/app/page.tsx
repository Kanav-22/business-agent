"use client";

import { useEffect, useState } from "react";
import {
  Banknote,
  Flame,
  Hourglass,
  ListTodo,
  TrendingUp,
  Users,
} from "lucide-react";
import { KpiCard } from "@/components/kpi-card";
import { RevenueChart } from "@/components/revenue-chart";
import { fmtMoney, fmtMonthLabel, getJson } from "@/lib/api";
import type { Kpis, MonthPoint } from "@/lib/types";

export default function OverviewPage() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [series, setSeries] = useState<MonthPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getJson<Kpis>("/api/kpis"),
      getJson<MonthPoint[]>("/api/chart/revenue-expenses"),
    ])
      .then(([k, s]) => {
        setKpis(k);
        setSeries(s);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-lg font-semibold">Overview</h1>
        <div className="mt-4 rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          Could not reach the backend ({error}). Start it with{" "}
          <code className="rounded bg-slate-900 px-1.5 py-0.5 text-xs">
            uvicorn app.main:app --reload
          </code>{" "}
          in <code className="text-xs">backend/</code>.
        </div>
      </div>
    );
  }

  if (!kpis || !series) {
    return (
      <div className="p-8 text-sm text-slate-500">Loading mission control…</div>
    );
  }

  const lastMonth = kpis.last_month ? fmtMonthLabel(kpis.last_month) : "—";
  const profit = kpis.last_month_profit;

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold">Overview</h1>
          <p className="text-sm text-slate-500">
            {kpis.company} · data through {lastMonth}
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          {lastMonth} P&L:{" "}
          <span
            className={profit >= 0 ? "text-emerald-400" : "text-orange-400"}
          >
            {profit >= 0 ? "+" : "−"}
            {fmtMoney(Math.abs(profit))}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="MRR"
          value={fmtMoney(kpis.mrr)}
          sub={
            kpis.revenue_mom_pct !== null
              ? `${kpis.revenue_mom_pct >= 0 ? "+" : ""}${kpis.revenue_mom_pct}% MoM billed`
              : undefined
          }
          icon={TrendingUp}
          accent="text-emerald-400"
        />
        <KpiCard
          label="Customers"
          value={String(kpis.active_customers)}
          sub="active accounts"
          icon={Users}
          accent="text-sky-400"
        />
        <KpiCard
          label="Cash"
          value={fmtMoney(kpis.cash, true)}
          sub="starting cash + net P&L"
          icon={Banknote}
          accent="text-slate-300"
        />
        <KpiCard
          label="Burn"
          value={fmtMoney(kpis.avg_monthly_burn, true)}
          sub="avg net, last 3 months"
          icon={Flame}
          accent="text-orange-400"
        />
        <KpiCard
          label="Runway"
          value={
            kpis.runway_months === null ? "∞" : `${kpis.runway_months} mo`
          }
          sub="cash ÷ avg burn"
          icon={Hourglass}
          accent="text-violet-400"
        />
        <KpiCard
          label="Open tasks"
          value={String(kpis.open_tasks)}
          sub="across departments"
          icon={ListTodo}
          accent="text-slate-300"
        />
      </div>

      <div className="mt-6">
        <RevenueChart data={series} />
      </div>
    </div>
  );
}
