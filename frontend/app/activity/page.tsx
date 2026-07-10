"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { AlertTriangle, Check, CornerDownRight, Loader2, RefreshCw } from "lucide-react";
import { getJson } from "@/lib/api";
import type { ActivityRun } from "@/lib/types";

const POLL_MS = 5000;

function timeAgo(ts: number): string {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function StatusCell({ run }: { run: ActivityRun }) {
  if (run.status === "running")
    return (
      <span className="flex items-center gap-1 text-slate-400">
        <Loader2 size={11} className="animate-spin" /> running
      </span>
    );
  if (run.status === "error")
    return (
      <span className="flex items-center gap-1 text-orange-400" title={run.error ?? ""}>
        <AlertTriangle size={11} /> {run.error}
      </span>
    );
  return (
    <span className="flex items-center gap-1 text-emerald-500/80">
      <Check size={11} /> ok
    </span>
  );
}

export default function ActivityPage() {
  const [runs, setRuns] = useState<ActivityRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    getJson<ActivityRun[]>("/api/activity?limit=100")
      .then((r) => {
        setRuns(r);
        setError(null);
      })
      .catch((e) => setError(String(e)));

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const totalCost = (runs ?? []).reduce((acc, r) => acc + (r.cost_usd || 0), 0);

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold">Agent Activity</h1>
          <p className="text-sm text-slate-500">
            Every agent run: who ran, why, tools, tokens and cost. Auto-refreshes.
          </p>
        </div>
        <div className="flex items-center gap-4">
          {runs && runs.length > 0 ? (
            <span className="text-xs text-slate-500">
              shown runs ≈ ${totalCost.toFixed(2)}
            </span>
          ) : null}
          <button
            onClick={load}
            className="flex items-center gap-1.5 rounded-lg border border-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-600 hover:text-slate-200"
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          Could not reach the backend ({error}).
        </div>
      ) : runs === null ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : runs.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-500">
          No agent runs yet — ask something in{" "}
          <a href="/chat" className="text-violet-400 hover:underline">
            Chat
          </a>{" "}
          and the delegation tree will land here.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Task</th>
                <th className="px-4 py-3 font-medium">Tools</th>
                <th className="px-4 py-3 font-medium text-right">Tokens</th>
                <th className="px-4 py-3 font-medium text-right">Cost</th>
                <th className="px-4 py-3 font-medium text-right">Duration</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.run_id}
                  className="border-b border-slate-800/60 text-xs last:border-b-0 hover:bg-slate-800/30"
                >
                  <td className="px-4 py-2.5">
                    <span
                      className={clsx("flex items-center gap-2", run.depth > 0 && "pl-4")}
                    >
                      {run.depth > 0 ? (
                        <CornerDownRight size={11} className="text-slate-600" />
                      ) : null}
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ background: run.color }}
                      />
                      <span className="font-medium" style={{ color: run.color }}>
                        {run.agent_display}
                      </span>
                    </span>
                  </td>
                  <td className="max-w-[280px] truncate px-4 py-2.5 text-slate-300" title={run.task}>
                    {run.task}
                  </td>
                  <td className="px-4 py-2.5 text-slate-400">
                    {run.tools.length
                      ? run.tools
                          .map((t) => (t.count > 1 ? `${t.tool}×${t.count}` : t.tool))
                          .join(", ")
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-400">
                    {(run.input_tokens + run.output_tokens).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-400">
                    ${run.cost_usd.toFixed(3)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-400">
                    {run.duration_ms != null ? `${(run.duration_ms / 1000).toFixed(1)}s` : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusCell run={run} />
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-500">
                    {timeAgo(run.started_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
