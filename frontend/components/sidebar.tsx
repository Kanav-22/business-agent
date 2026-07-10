"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  Activity,
  Database,
  FileText,
  Inbox,
  LayoutDashboard,
  MessageSquare,
  Sparkles,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/chat", label: "Chat with CEO", icon: MessageSquare },
  { href: "/activity", label: "Agent Activity", icon: Activity },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/approvals", label: "Approvals", icon: Inbox },
];

const UPCOMING = [{ label: "Data", icon: Database, phase: "Phase 5" }];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950 px-3 py-5">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/20 text-violet-300">
          <Sparkles size={16} />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">Lumina Labs</div>
          <div className="text-[11px] text-slate-500">AI Business OS</div>
        </div>
      </div>

      <nav className="space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              pathname === href
                ? "bg-slate-800/80 text-slate-100"
                : "text-slate-400 hover:bg-slate-900 hover:text-slate-200",
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>

      <div className="mt-6 border-t border-slate-800/70 pt-4">
        <div className="px-3 pb-2 text-[10px] font-medium uppercase tracking-wider text-slate-600">
          Coming soon
        </div>
        {UPCOMING.map(({ label, icon: Icon, phase }) => (
          <div
            key={label}
            className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600"
            title={`Arrives in ${phase}`}
          >
            <Icon size={16} />
            <span className="flex-1">{label}</span>
            <span className="rounded border border-slate-800 px-1.5 py-0.5 text-[9px] text-slate-600">
              {phase}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-auto px-3 text-[11px] leading-relaxed text-slate-600">
        Phase 4 — content team
        <br />
        + human-in-the-loop approvals
        <br />+ scheduled competitor scans
      </div>
    </aside>
  );
}
