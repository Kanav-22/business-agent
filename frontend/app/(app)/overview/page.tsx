"use client";

import { useEffect, useState } from "react";
import {
  Banknote,
  ChevronDown,
  ChevronUp,
  Flame,
  Hourglass,
  ListTodo,
  Newspaper,
  TrendingUp,
  Users,
} from "lucide-react";
import { KpiCard } from "@/components/kpi-card";
import { Markdown } from "@/components/markdown";
import { PageHeader, PageHeaderSkeleton } from "@/components/page-header";
import { RevenueChart } from "@/components/revenue-chart";
import { fmtMoney, fmtMonthLabel, getJson } from "@/lib/api";
import type { Kpis, MonthPoint, ReportDetail } from "@/lib/types";

function BriefingCard({ briefing }: { briefing: ReportDetail | null }) {
  const [expanded, setExpanded] = useState(false);
  if (!briefing) {
    return (
      <div className="mb-6 flex items-center gap-3 rounded-xl border border-dashed border-slate-800 px-4 py-3 text-xs text-slate-500">
        <Newspaper size={14} />
        No weekly briefing yet — one is generated every Monday 06:20, or trigger it
        from the Reports page.
      </div>
    );
  }
  return (
    <div className="mb-6 rounded-xl border border-violet-900/50 bg-violet-950/20 p-4">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-2 text-left"
      >
        <Newspaper size={14} className="text-violet-400" />
        <span className="text-sm font-medium text-violet-200">{briefing.title}</span>
        <span className="ml-auto flex items-center gap-1 text-[11px] text-slate-500">
          {new Date(briefing.created_at).toLocaleDateString()}
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>
      <div
        className={
          expanded ? "mt-3" : "mt-3 max-h-28 overflow-hidden [mask-image:linear-gradient(to_bottom,black_55%,transparent)]"
        }
      >
        <Markdown>{briefing.content.replace(/^# .*\n/, "")}</Markdown>
      </div>
    </div>
  );
}

export default function OverviewPage() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [series, setSeries] = useState<MonthPoint[] | null>(null);
  const [briefing, setBriefing] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getJson<Kpis>("/api/kpis"),
      getJson<MonthPoint[]>("/api/chart/revenue-expenses"),
      getJson<{ report: ReportDetail | null }>("/api/briefing").catch(() => ({
        report: null,
      })),
    ])
      .then(([k, s, b]) => {
        setKpis(k);
        setSeries(s);
        setBriefing(b.report);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">
        <PageHeader
          title="Overview"
          subtitle="Business performance, cash position, and current operating priorities."
        />
        <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
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
      <div className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">
        <PageHeaderSkeleton />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6" role="status">
          {Array.from({ length: 6 }, (_, index) => (
            <div
              key={index}
              className="h-28 animate-pulse rounded-xl border border-slate-800 bg-slate-900 motion-reduce:animate-none"
            />
          ))}
          <span className="sr-only">Loading mission control…</span>
        </div>
        <div className="mt-6 h-80 animate-pulse rounded-xl border border-slate-800 bg-slate-900 motion-reduce:animate-none" />
      </div>
    );
  }

  const lastMonth = kpis.last_month ? fmtMonthLabel(kpis.last_month) : "—";
  const profit = kpis.last_month_profit;

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Overview"
        subtitle={`${kpis.company} · data through ${lastMonth}`}
        actions={
          <div className="text-left text-xs text-slate-500 sm:text-right">
          {lastMonth} P&L:{" "}
          <span
            className={profit >= 0 ? "text-emerald-400" : "text-orange-400"}
          >
            {profit >= 0 ? "+" : "−"}
            {fmtMoney(Math.abs(profit))}
          </span>
          </div>
        }
      />

      <BriefingCard briefing={briefing} />

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
