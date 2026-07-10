"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { Check, Inbox, Loader2, X } from "lucide-react";
import { Markdown } from "@/components/markdown";
import { API_BASE, getJson } from "@/lib/api";
import type { Approval } from "@/lib/types";

const POLL_MS = 5000;

function StatusBadge({ status }: { status: Approval["status"] }) {
  const styles: Record<Approval["status"], string> = {
    pending: "border-amber-800 bg-amber-950/40 text-amber-300",
    approved: "border-emerald-800 bg-emerald-950/40 text-emerald-300",
    rejected: "border-slate-700 bg-slate-800/40 text-slate-400",
  };
  return (
    <span className={clsx("rounded border px-1.5 py-0.5 text-[10px]", styles[status])}>
      {status}
    </span>
  );
}

function PendingCard({
  approval,
  onDecided,
}: {
  approval: Approval;
  onDecided: () => void;
}) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const decide = async (action: "approve" | "reject") => {
    setBusy(action);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/approvals/${approval.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: note.trim() || null }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onDecided();
    } catch (e) {
      setError(String(e));
      setBusy(null);
    }
  };

  return (
    <div className="rounded-xl border border-amber-900/50 bg-slate-900 p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-100">{approval.title}</span>
        <span className="rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">
          {approval.channel}
        </span>
        <span className="text-[11px] text-slate-500">
          by {approval.agent} · {new Date(approval.created_at).toLocaleString()}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => decide("approve")}
            disabled={busy !== null}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy === "approve" ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Check size={12} />
            )}
            Approve & publish
          </button>
          <button
            onClick={() => decide("reject")}
            disabled={busy !== null}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 disabled:opacity-50"
          >
            {busy === "reject" ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <X size={12} />
            )}
            Reject
          </button>
        </div>
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
        <Markdown>{approval.content}</Markdown>
      </div>
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional note (e.g. why rejected)…"
        className="mt-2 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 placeholder:text-slate-600 focus:border-slate-600 focus:outline-none"
      />
      {error ? <div className="mt-2 text-xs text-orange-400">{error}</div> : null}
    </div>
  );
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getJson<Approval[]>("/api/approvals?limit=100")
      .then((a) => {
        setApprovals(a);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  const pending = (approvals ?? []).filter((a) => a.status === "pending");
  const decided = (approvals ?? []).filter((a) => a.status !== "pending");

  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Approvals</h1>
        <p className="text-sm text-slate-500">
          Outward-facing agent work waits here. Nothing is published without your
          click — approving moves a draft to the Reports library.
        </p>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          Could not reach the backend ({error}).
        </div>
      ) : approvals === null ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : (
        <>
          {pending.length === 0 ? (
            <div className="flex items-center gap-3 rounded-xl border border-dashed border-slate-800 px-4 py-6 text-sm text-slate-500">
              <Inbox size={16} />
              Inbox zero — ask the CMO to draft something in Chat (e.g. “Draft a
              launch announcement for usage-based billing”).
            </div>
          ) : (
            <div className="space-y-4">
              {pending.map((a) => (
                <PendingCard key={a.id} approval={a} onDecided={load} />
              ))}
            </div>
          )}

          {decided.length > 0 ? (
            <div className="mt-8">
              <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-600">
                Decision history
              </h2>
              <div className="space-y-2">
                {decided.map((a) => (
                  <details
                    key={a.id}
                    className="rounded-xl border border-slate-800 bg-slate-900"
                  >
                    <summary className="flex cursor-pointer select-none flex-wrap items-center gap-2 px-4 py-2.5 text-sm text-slate-300">
                      <StatusBadge status={a.status} />
                      <span className="font-medium">{a.title}</span>
                      <span className="text-[11px] text-slate-500">
                        {a.channel} · decided{" "}
                        {a.decided_at ? new Date(a.decided_at).toLocaleString() : "—"}
                      </span>
                      {a.note ? (
                        <span className="text-[11px] italic text-slate-500">
                          “{a.note}”
                        </span>
                      ) : null}
                    </summary>
                    <div className="border-t border-slate-800/70 p-4">
                      <Markdown>{a.content}</Markdown>
                    </div>
                  </details>
                ))}
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
