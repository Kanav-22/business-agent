"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MonthPoint } from "@/lib/types";
import { fmtMoney, fmtMonthLabel } from "@/lib/api";

// Series colors validated (dataviz six checks) against surface #0f172a.
const REVENUE = "#199e70";
const EXPENSES = "#d95926";

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-medium text-slate-300">{fmtMonthLabel(label)}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 py-0.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.stroke }}
          />
          <span className="w-16 capitalize text-slate-400">{p.dataKey}</span>
          <span className="tabular-nums text-slate-200">{fmtMoney(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function RevenueChart({ data }: { data: MonthPoint[] }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-1 text-sm font-medium text-slate-200">
        Revenue vs expenses
      </div>
      <div className="mb-4 text-xs text-slate-500">
        Monthly, last {data.length} months
      </div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="month"
              tickFormatter={fmtMonthLabel}
              tick={{ fill: "#64748b", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
              interval="preserveStartEnd"
              minTickGap={24}
            />
            <YAxis
              tickFormatter={(v: number) => fmtMoney(v, true)}
              tick={{ fill: "#64748b", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={56}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#475569" }} />
            <Legend
              formatter={(value: string) => (
                <span className="text-xs capitalize text-slate-400">{value}</span>
              )}
              iconType="plainline"
            />
            <Line
              type="monotone"
              dataKey="revenue"
              stroke={REVENUE}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "#0f172a" }}
            />
            <Line
              type="monotone"
              dataKey="expenses"
              stroke={EXPENSES}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "#0f172a" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
