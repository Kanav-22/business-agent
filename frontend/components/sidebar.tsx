"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  Activity,
  ArrowLeft,
  ClipboardList,
  Database,
  FileText,
  Inbox,
  LayoutDashboard,
  MessageSquare,
  Rocket,
} from "lucide-react";
import { LogoMark } from "@/components/logo-mark";
import { BRAND } from "@/lib/brand";

const NAV = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/chat", label: "Chat with CEO", icon: MessageSquare },
  { href: "/activity", label: "Agent Activity", icon: Activity },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/approvals", label: "Approvals", icon: Inbox },
  { href: "/venture", label: "Venture Studio", icon: Rocket },
  { href: "/onboarding", label: "Business Setup", icon: ClipboardList },
];

const UPCOMING = [{ label: "Data", icon: Database, phase: "Phase 5" }];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950 px-3 py-5">
      <Link
        href="/overview"
        className="mb-8 flex min-h-11 items-center gap-3 rounded-xl px-2 text-slate-100 outline-none transition-colors hover:bg-slate-900 focus-visible:ring-2 focus-visible:ring-violet-400"
        aria-label={`${BRAND.name} overview`}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-violet-800/70 bg-violet-500/10 text-violet-300">
          <LogoMark className="h-7 w-7" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold leading-tight">{BRAND.name}</span>
          <span className="block text-[11px] text-slate-400">Executive command center</span>
        </span>
      </Link>

      <nav className="space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={pathname === href ? "page" : undefined}
            className={clsx(
              "flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-violet-400",
              pathname === href
                ? "bg-slate-800/80 text-slate-100"
                : "text-slate-400 hover:bg-slate-900 hover:text-slate-200",
            )}
          >
            <Icon size={16} aria-hidden="true" />
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

      <Link
        href="/"
        className="mt-auto flex min-h-11 items-center gap-2 rounded-lg px-3 text-xs text-slate-400 outline-none transition-colors hover:bg-slate-900 hover:text-slate-200 focus-visible:ring-2 focus-visible:ring-violet-400"
      >
        <ArrowLeft size={14} aria-hidden="true" />
        Website
      </Link>
    </aside>
  );
}
