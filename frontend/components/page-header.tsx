import type { ReactNode } from "react";
import clsx from "clsx";

export function PageHeader({
  title,
  subtitle,
  eyebrow,
  actions,
  className,
}: {
  title: string;
  subtitle?: ReactNode;
  eyebrow?: string;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={clsx(
        "mb-6 flex min-w-0 flex-col gap-4 border-b border-slate-800/80 pb-5 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-1 text-xs font-medium uppercase tracking-[0.16em] text-violet-400">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-xl font-semibold tracking-tight text-slate-100 sm:text-2xl">
          {title}
        </h1>
        {subtitle ? (
          <div className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">
            {subtitle}
          </div>
        ) : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </header>
  );
}

export function PageHeaderSkeleton() {
  return (
    <div
      className="mb-6 border-b border-slate-800/80 pb-5"
      role="status"
      aria-label="Loading page"
    >
      <div className="h-7 w-44 animate-pulse rounded bg-slate-800 motion-reduce:animate-none" />
      <div className="mt-2 h-4 w-full max-w-md animate-pulse rounded bg-slate-900 motion-reduce:animate-none" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}
