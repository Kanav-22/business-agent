"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { Download, FileText, Loader2, Play, ShieldCheck, Newspaper } from "lucide-react";
import { Markdown } from "@/components/markdown";
import { API_BASE, getJson } from "@/lib/api";
import type { ReportDetail, ReportSummary } from "@/lib/types";

const POLL_MS = 5000;

const KIND_META: Record<
  ReportSummary["kind"],
  { label: string; className: string }
> = {
  report: { label: "report", className: "border-lime-800 bg-lime-950/40 text-lime-300" },
  briefing: { label: "briefing", className: "border-violet-800 bg-violet-950/40 text-violet-300" },
  control_check: { label: "control check", className: "border-rose-800 bg-rose-950/40 text-rose-300" },
  research: { label: "research", className: "border-amber-800 bg-amber-950/40 text-amber-300" },
  content: { label: "published content", className: "border-fuchsia-800 bg-fuchsia-950/40 text-fuchsia-300" },
};

function JobButton({
  job,
  label,
  icon: Icon,
  onDone,
}: {
  job: string;
  label: string;
  icon: typeof Play;
  onDone: () => void;
}) {
  const [state, setState] = useState<"idle" | "running" | "error">("idle");

  const trigger = async () => {
    setState("running");
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${job}/run`, { method: "POST" });
      if (!res.ok && res.status !== 409) throw new Error(String(res.status));
      // job runs async server-side; give it a while, list polling picks it up
      setTimeout(() => {
        setState("idle");
        onDone();
      }, 4000);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  };

  return (
    <button
      onClick={trigger}
      disabled={state === "running"}
      className={clsx(
        "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors",
        state === "error"
          ? "border-orange-800 text-orange-300"
          : "border-slate-800 text-slate-400 hover:border-slate-600 hover:text-slate-200",
      )}
      title="Runs the agents on the backend (requires ANTHROPIC_API_KEY)"
    >
      {state === "running" ? (
        <Loader2 size={12} className="animate-spin" />
      ) : (
        <Icon size={12} />
      )}
      {state === "error" ? "failed — check backend" : label}
    </button>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [selected, setSelected] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getJson<ReportSummary[]>("/api/reports?limit=100")
      .then((r) => {
        setReports(r);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  const open = (id: number) =>
    getJson<ReportDetail>(`/api/reports/${id}`).then(setSelected).catch(() => {});

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Reports</h1>
          <p className="text-sm text-slate-500">
            Generated documents — weekly briefings and control checks arrive every
            Monday morning on their own.
          </p>
        </div>
        <div className="flex gap-2">
          <JobButton
            job="weekly_control"
            label="Run control check"
            icon={ShieldCheck}
            onDone={load}
          />
          <JobButton
            job="weekly_briefing"
            label="Generate briefing"
            icon={Newspaper}
            onDone={load}
          />
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          Could not reach the backend ({error}).
        </div>
      ) : reports === null ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : reports.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-500">
          No reports yet. Use the buttons above, ask the Reporting agent for a P&L
          in Chat, or wait for Monday 06:00.
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[320px,1fr]">
          <div className="space-y-2">
            {reports.map((r) => (
              <button
                key={r.id}
                onClick={() => open(r.id)}
                className={clsx(
                  "w-full rounded-xl border p-3 text-left transition-colors",
                  selected?.id === r.id
                    ? "border-slate-600 bg-slate-800/60"
                    : "border-slate-800 bg-slate-900 hover:border-slate-700",
                )}
              >
                <div className="flex items-center gap-2">
                  <FileText size={13} className="shrink-0 text-slate-500" />
                  <span className="truncate text-sm font-medium text-slate-200">
                    {r.title}
                  </span>
                </div>
                <div className="mt-1.5 flex items-center gap-2 text-[11px] text-slate-500">
                  <span
                    className={clsx(
                      "rounded border px-1.5 py-0.5",
                      KIND_META[r.kind]?.className ?? "border-slate-700",
                    )}
                  >
                    {KIND_META[r.kind]?.label ?? r.kind}
                  </span>
                  <span>{r.agent}</span>
                  <span>·</span>
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-xs text-slate-500">{r.excerpt}</p>
              </button>
            ))}
          </div>

          <div className="min-w-0">
            {selected ? (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
                <div className="mb-4 flex items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div className="text-xs text-slate-500">
                    {selected.agent} · {new Date(selected.created_at).toLocaleString()}
                  </div>
                  <a
                    href={`${API_BASE}/api/reports/${selected.id}/download`}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-600 hover:text-slate-200"
                  >
                    <Download size={12} /> Markdown
                  </a>
                </div>
                <Markdown>{selected.content}</Markdown>
              </div>
            ) : (
              <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-800 text-sm text-slate-600">
                Select a report to read it
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
