import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { LogoMark } from "@/components/logo-mark";
import { BRAND } from "@/lib/brand";

const REPO_URL = "https://github.com/Kanav-22/business-agent";
const DOCS_REVISION = "d7130e908fdfe9f0340a53830dcb0d8d5efda7d2";
const TEMPLATE_URL = `${REPO_URL}/blob/${DOCS_REVISION}/OS_TEMPLATE.md`;

export const metadata: Metadata = {
  title: BRAND.name,
  description: BRAND.tagline,
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh overflow-x-hidden bg-[#0a0f1a] text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#0a0f1a]/85 backdrop-blur-xl">
        <nav
          aria-label="Marketing navigation"
          className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8"
        >
          <Link
            href="/"
            className="flex min-h-11 items-center gap-2.5 rounded-lg text-sm font-semibold tracking-tight text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
          >
            <LogoMark className="h-8 w-8 text-violet-400" />
            <span>{BRAND.name}</span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-5">
            <a
              href="#how-it-works"
              className="hidden min-h-11 items-center rounded-lg px-2 text-sm text-slate-400 transition-colors hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 motion-reduce:transition-none sm:flex"
            >
              How it works
            </a>
            <a
              href="#systems"
              className="hidden min-h-11 items-center rounded-lg px-2 text-sm text-slate-400 transition-colors hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 motion-reduce:transition-none md:flex"
            >
              Systems
            </a>
            <Link
              href="/overview"
              className="flex min-h-11 items-center rounded-lg border border-violet-400/35 bg-violet-400/10 px-3 text-sm font-medium text-violet-200 transition-colors hover:border-violet-300/60 hover:bg-violet-400/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 motion-reduce:transition-none sm:px-4"
            >
              Dashboard
            </Link>
          </div>
        </nav>
      </header>

      <main id="main-content">{children}</main>

      <footer className="border-t border-white/[0.06] bg-[#080c15]">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1fr,auto] md:items-end lg:px-8">
          <div>
            <Link
              href="/"
              className="inline-flex min-h-11 items-center gap-2.5 rounded-lg text-sm font-semibold text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
            >
              <LogoMark className="h-8 w-8 text-violet-400" />
              {BRAND.name}
            </Link>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">{BRAND.tagline}</p>
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-400">
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
            >
              GitHub <ArrowUpRight size={14} aria-hidden="true" />
            </a>
            <a
              href={TEMPLATE_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
            >
              Built with the OS Template <ArrowUpRight size={14} aria-hidden="true" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
