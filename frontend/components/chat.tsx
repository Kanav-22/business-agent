"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  AlertTriangle,
  Check,
  CornerDownRight,
  Loader2,
  Send,
  Wrench,
} from "lucide-react";
import { WS_CHAT_URL } from "@/lib/api";
import type { AgentEvent } from "@/lib/types";

/* ------------------------------------------------------------------ model */

interface ToolItem {
  kind: "tool";
  id?: string;
  tool?: string;
  input?: Record<string, unknown>;
  output?: string;
  isError?: boolean;
}
interface TextItem {
  kind: "text";
  text: string;
}
interface ChildItem {
  kind: "child";
  runId: string;
}
type RunItem = ToolItem | TextItem | ChildItem;

interface RunNode {
  id: string;
  agent: string;
  display: string;
  color: string;
  depth: number;
  task?: string;
  items: RunItem[];
  status: "running" | "done" | "error";
  error?: string | null;
  durationMs?: number;
}

interface Exchange {
  user: string;
  events: AgentEvent[];
  done?: AgentEvent;
  errorMessage?: string;
}

function buildTree(events: AgentEvent[]) {
  const runs = new Map<string, RunNode>();
  const roots: string[] = [];
  for (const e of events) {
    if (e.type === "run_started" && e.run_id) {
      runs.set(e.run_id, {
        id: e.run_id,
        agent: e.agent ?? "?",
        display: e.agent_display ?? e.agent ?? "?",
        color: e.color ?? "#94a3b8",
        depth: e.depth ?? 0,
        task: e.task,
        items: [],
        status: "running",
      });
      if (e.parent_run_id && runs.has(e.parent_run_id)) {
        runs.get(e.parent_run_id)!.items.push({ kind: "child", runId: e.run_id });
      } else {
        roots.push(e.run_id);
      }
      continue;
    }
    const node = e.run_id ? runs.get(e.run_id) : undefined;
    if (!node) continue;
    if (e.type === "agent_text" && e.text) {
      node.items.push({ kind: "text", text: e.text });
    } else if (e.type === "tool_call") {
      node.items.push({
        kind: "tool",
        id: e.tool_use_id,
        tool: e.tool,
        input: e.input,
      });
    } else if (e.type === "tool_result") {
      const item = [...node.items]
        .reverse()
        .find((i): i is ToolItem => i.kind === "tool" && i.id === e.tool_use_id);
      if (item) {
        item.output = e.output;
        item.isError = e.is_error;
      }
    } else if (e.type === "run_completed") {
      node.status = e.error ? "error" : "done";
      node.error = e.error;
      node.durationMs = e.duration_ms;
    }
  }
  return { runs, roots };
}

/* ------------------------------------------------------------- components */

function StatusBadge({ node }: { node: RunNode }) {
  if (node.status === "running")
    return (
      <span className="flex items-center gap-1 text-[11px] text-slate-400">
        <Loader2 size={11} className="animate-spin" /> working…
      </span>
    );
  if (node.status === "error")
    return (
      <span className="flex items-center gap-1 text-[11px] text-orange-400">
        <AlertTriangle size={11} /> {node.error}
      </span>
    );
  return (
    <span className="flex items-center gap-1 text-[11px] text-slate-500">
      <Check size={11} />
      {node.durationMs != null ? `${(node.durationMs / 1000).toFixed(1)}s` : "done"}
    </span>
  );
}

function ToolCall({ item }: { item: ToolItem }) {
  const isDelegate = item.tool === "delegate_to_agent";
  return (
    <details className="group rounded-lg border border-slate-800 bg-slate-950/60">
      <summary className="flex cursor-pointer select-none items-center gap-2 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200">
        {isDelegate ? <CornerDownRight size={12} /> : <Wrench size={12} />}
        <span className="font-mono">{item.tool}</span>
        {isDelegate && item.input?.agent ? (
          <span className="text-slate-500">→ {String(item.input.agent)}</span>
        ) : null}
        {item.output === undefined ? (
          <Loader2 size={11} className="ml-auto animate-spin text-slate-500" />
        ) : item.isError ? (
          <span className="ml-auto text-orange-400">error</span>
        ) : null}
      </summary>
      <div className="space-y-2 border-t border-slate-800/70 px-3 py-2">
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-600">
            input
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded bg-slate-900 p-2 text-[11px] leading-relaxed text-slate-300">
            {JSON.stringify(item.input, null, 2)}
          </pre>
        </div>
        {item.output !== undefined && (
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-600">
              result
            </div>
            <pre
              className={clsx(
                "max-h-64 overflow-auto whitespace-pre-wrap break-words rounded bg-slate-900 p-2 text-[11px] leading-relaxed",
                item.isError ? "text-orange-300" : "text-slate-300",
              )}
            >
              {item.output}
            </pre>
          </div>
        )}
      </div>
    </details>
  );
}

function RunBlock({
  runId,
  runs,
}: {
  runId: string;
  runs: Map<string, RunNode>;
}) {
  const node = runs.get(runId);
  if (!node) return null;
  return (
    <div
      className="rounded-xl border border-slate-800 bg-slate-900/70 p-3"
      style={{ borderLeft: `3px solid ${node.color}` }}
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-slate-950"
          style={{ background: node.color }}
        >
          {node.display.slice(0, 2).toUpperCase()}
        </span>
        <span className="text-sm font-medium" style={{ color: node.color }}>
          {node.display}
        </span>
        {node.depth > 0 && node.task ? (
          <span className="truncate text-xs italic text-slate-500" title={node.task}>
            “{node.task}”
          </span>
        ) : null}
        <div className="ml-auto">
          <StatusBadge node={node} />
        </div>
      </div>
      <div className="space-y-2">
        {node.items.map((item, i) => {
          if (item.kind === "text")
            return (
              <p
                key={i}
                className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200"
              >
                {item.text}
              </p>
            );
          if (item.kind === "tool") return <ToolCall key={i} item={item} />;
          return (
            <div key={i} className="pl-4">
              <RunBlock runId={item.runId} runs={runs} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ExchangeView({ exchange }: { exchange: Exchange }) {
  const { runs, roots } = buildTree(exchange.events);
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <div className="max-w-xl rounded-2xl rounded-br-sm bg-violet-600/90 px-4 py-2 text-sm text-white">
          {exchange.user}
        </div>
      </div>
      {roots.map((id) => (
        <RunBlock key={id} runId={id} runs={runs} />
      ))}
      {exchange.errorMessage ? (
        <div className="rounded-lg border border-orange-900/60 bg-orange-950/30 px-3 py-2 text-xs text-orange-300">
          {exchange.errorMessage}
        </div>
      ) : null}
      {exchange.done?.usage ? (
        <div className="text-right text-[11px] text-slate-600">
          {exchange.done.usage.input_tokens?.toLocaleString()} in ·{" "}
          {exchange.done.usage.output_tokens?.toLocaleString()} out tokens ·{" "}
          {((exchange.done.duration_ms ?? 0) / 1000).toFixed(1)}s
        </div>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------- page */

const SUGGESTIONS = [
  "What was our profit last month and what's our runway?",
  "How is MRR trending over the last 6 months?",
  "What are our three biggest expense categories this year?",
  "How much do we spend on payroll versus everything else?",
];

export function Chat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const closedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_CHAT_URL);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setBusy(false);
      if (!closedRef.current) setTimeout(connect, 1500);
    };
    ws.onmessage = (msg) => {
      const event: AgentEvent = JSON.parse(msg.data);
      setExchanges((prev) => {
        if (!prev.length) return prev;
        const next = [...prev];
        const current = { ...next[next.length - 1] };
        if (event.type === "done") {
          current.done = event;
        } else if (event.type === "error") {
          current.errorMessage = event.message;
        } else {
          current.events = [...current.events, event];
        }
        next[next.length - 1] = current;
        return next;
      });
      if (event.type === "done" || event.type === "error") setBusy(false);
    };
  }, []);

  useEffect(() => {
    closedRef.current = false;
    connect();
    return () => {
      closedRef.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [exchanges]);

  const send = (text: string) => {
    const message = text.trim();
    if (!message || busy || !connected) return;
    setExchanges((prev) => [...prev, { user: message, events: [] }]);
    wsRef.current?.send(JSON.stringify({ message }));
    setBusy(true);
    setInput("");
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="border-b border-slate-800 px-8 py-4">
        <h1 className="text-lg font-semibold">Chat with the CEO</h1>
        <p className="text-sm text-slate-500">
          Ask anything about the business — watch the CEO delegate to specialists live.
        </p>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-8 py-6">
        {exchanges.length === 0 ? (
          <div className="mx-auto mt-16 max-w-lg text-center">
            <div className="text-sm text-slate-400">
              Try one of these to see the delegation tree:
            </div>
            <div className="mt-4 grid gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  disabled={!connected || busy}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-2.5 text-left text-sm text-slate-300 transition-colors hover:border-slate-600 hover:text-slate-100 disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          exchanges.map((ex, i) => <ExchangeView key={i} exchange={ex} />)
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-800 px-8 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex items-center gap-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              connected
                ? "Ask the CEO about the business…"
                : "Connecting to backend…"
            }
            disabled={!connected || busy}
            className="flex-1 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-violet-500/60 focus:outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!connected || busy || !input.trim()}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600 text-white transition-colors hover:bg-violet-500 disabled:opacity-40"
          >
            {busy ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </form>
        <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-600">
          <span
            className={clsx(
              "inline-block h-1.5 w-1.5 rounded-full",
              connected ? "bg-emerald-500" : "bg-orange-500",
            )}
          />
          {connected ? "Connected" : "Reconnecting…"} · requires ANTHROPIC_API_KEY
          on the backend
        </div>
      </div>
    </div>
  );
}
