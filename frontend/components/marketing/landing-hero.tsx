"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowDown, ArrowRight } from "lucide-react";
import { HeroSceneShell } from "@/components/three/hero-scene-shell";
import { BRAND } from "@/lib/brand";

export function LandingHero() {
  const [pulseSignal, setPulseSignal] = useState(0);
  const pulse = () => setPulseSignal((current) => current + 1);

  return (
    <section className="relative isolate overflow-hidden border-b border-white/[0.06]">
      <div
        className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(circle_at_75%_35%,rgba(167,139,250,0.13),transparent_34%),radial-gradient(circle_at_35%_65%,rgba(34,211,238,0.05),transparent_32%),linear-gradient(145deg,#0a0f1a_0%,#101827_100%)]"
        aria-hidden="true"
      />
      <div className="mx-auto grid min-h-[calc(100dvh-4rem)] max-w-6xl items-center gap-10 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-[0.92fr,1.08fr] lg:gap-6 lg:px-8 lg:py-24">
        <div className="relative z-10 max-w-xl">
          <p className="mb-5 inline-flex rounded-full border border-violet-400/20 bg-violet-400/[0.07] px-3 py-1.5 text-xs font-medium uppercase tracking-[0.18em] text-violet-200">
            AI operating system for owner-led businesses
          </p>
          <h1 className="text-balance text-5xl font-semibold tracking-tight text-slate-50 sm:text-6xl lg:text-7xl">
            {BRAND.name}
          </h1>
          <p className="mt-6 max-w-lg text-pretty text-xl font-medium leading-8 tracking-tight text-slate-200 sm:text-2xl">
            One CEO. Nine specialists. One command center for your business.
          </p>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-400 sm:text-lg">
            Ask a question. The CEO delegates to finance, marketing, technology,
            research, and coordination agents, then returns one decision trail.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/overview"
              onPointerEnter={pulse}
              onFocus={pulse}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-violet-400 px-5 text-sm font-semibold text-slate-950 transition-colors hover:bg-violet-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0f1a] motion-reduce:transition-none"
            >
              Open the dashboard <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-5 text-sm font-medium text-slate-200 transition-colors hover:border-white/20 hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 motion-reduce:transition-none"
            >
              See how it works <ArrowDown size={16} aria-hidden="true" />
            </a>
          </div>
          <p className="mt-6 text-xs leading-5 text-slate-400">
            Demo mode runs without model API spend. Auth, billing, and multi-tenant
            deployment are not included yet.
          </p>
        </div>

        <div
          className="relative h-[420px] min-w-0 overflow-hidden rounded-[2rem] border border-white/[0.06] bg-[#0c1321]/60 sm:h-[520px] lg:h-[620px]"
          role="img"
          aria-label="A constellation showing the CEO connected to nine specialist agents"
        >
          <HeroSceneShell pulseSignal={pulseSignal} className="h-full w-full" />
          <div className="pointer-events-none absolute inset-x-5 bottom-5 flex items-center justify-between rounded-xl border border-white/[0.06] bg-[#0a0f1a]/70 px-4 py-3 text-xs text-slate-400 backdrop-blur-md">
            <span className="inline-flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
              CEO delegation map
            </span>
            <span className="font-mono text-[11px] text-cyan-300/80">10 agents</span>
          </div>
        </div>
      </div>
    </section>
  );
}
