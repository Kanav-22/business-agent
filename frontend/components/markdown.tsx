"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Dark-theme markdown renderer for agent-generated reports. */
export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: (props) => (
          <h1 className="mb-3 mt-1 text-xl font-semibold text-slate-100" {...props} />
        ),
        h2: (props) => (
          <h2 className="mb-2 mt-5 text-base font-semibold text-slate-200" {...props} />
        ),
        h3: (props) => (
          <h3 className="mb-1.5 mt-4 text-sm font-semibold text-slate-200" {...props} />
        ),
        p: (props) => (
          <p className="mb-3 text-sm leading-relaxed text-slate-300" {...props} />
        ),
        ul: (props) => (
          <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-slate-300" {...props} />
        ),
        ol: (props) => (
          <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-slate-300" {...props} />
        ),
        li: (props) => <li className="leading-relaxed" {...props} />,
        strong: (props) => <strong className="font-semibold text-slate-100" {...props} />,
        em: (props) => <em className="text-slate-400" {...props} />,
        code: (props) => (
          <code
            className="rounded bg-slate-800 px-1 py-0.5 font-mono text-[12px] text-slate-200"
            {...props}
          />
        ),
        pre: (props) => (
          <pre
            className="mb-3 overflow-x-auto rounded-lg bg-slate-950 p-3 text-[12px]"
            {...props}
          />
        ),
        blockquote: (props) => (
          <blockquote
            className="mb-3 border-l-2 border-amber-500/60 pl-3 text-sm text-amber-200/90"
            {...props}
          />
        ),
        table: (props) => (
          <div className="mb-3 overflow-x-auto">
            <table className="w-full border-collapse text-sm" {...props} />
          </div>
        ),
        th: (props) => (
          <th
            className="border-b border-slate-700 px-2 py-1.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-400"
            {...props}
          />
        ),
        td: (props) => (
          <td
            className="border-b border-slate-800/70 px-2 py-1.5 tabular-nums text-slate-300"
            {...props}
          />
        ),
        a: (props) => (
          <a className="text-violet-400 hover:underline" target="_blank" rel="noreferrer" {...props} />
        ),
        hr: () => <hr className="my-4 border-slate-800" />,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
