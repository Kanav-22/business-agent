import type { SVGProps } from "react";
import {
  ArrowUpRight,
  Database,
  GitBranch,
  SquareTerminal,
  type LucideIcon,
} from "lucide-react";
import { LandingHero } from "@/components/marketing/landing-hero";

const REPO_URL = "https://github.com/Kanav-22/business-agent";
const DOCS_REVISION = "d7130e908fdfe9f0340a53830dcb0d8d5efda7d2";

const AGENT_TEAMS = [
  {
    name: "Core",
    description: "Routes, reasons, and coordinates the operating company.",
    agents: [
      ["CEO", "#a78bfa"],
      ["CFO", "#34d399"],
      ["CMO", "#f472b6"],
      ["CTO", "#38bdf8"],
      ["Researcher", "#fbbf24"],
      ["Coordinator", "#94a3b8"],
      ["Content", "#e879f9"],
    ],
  },
  {
    name: "Finance",
    description: "Checks the numbers before advice reaches the boardroom.",
    agents: [
      ["FP&A", "#2dd4bf"],
      ["Reporting", "#a3e635"],
      ["Revenue", "#4ade80"],
      ["Control", "#fb7185"],
    ],
  },
  {
    name: "Venture",
    description: "Tests ideas, execution, demand, and downside risk.",
    agents: [
      ["CEO (Venture)", "#c084fc"],
      ["CFO (Venture)", "#10b981"],
      ["CMO (Venture)", "#f9a8d4"],
      ["CTO (Venture)", "#7dd3fc"],
      ["COO", "#fdba74"],
      ["Risk Officer", "#f87171"],
      ["Red Team", "#ef4444"],
      ["Sales", "#facc15"],
      ["Interviewer", "#a3a3a3"],
      ["Idea Scorer", "#22d3ee"],
    ],
  },
] as const;

const SYSTEMS = [
  [
    "Agent Evaluation System",
    "Eighteen scenario cases, a deterministic 0–10 rubric, persisted results, and a CLI runner.",
  ],
  [
    "Model Downgrade Survival Kit",
    "Nine role guides can be injected at runtime when a smaller model needs more structure.",
  ],
  [
    "Prompt Router",
    "Fifteen deterministic rules route requests, escalate domain risk, and flag founder-fit concerns.",
  ],
  [
    "Agent Debate System",
    "Finance, demand, feasibility, execution, and risk objections are weighed before the CEO decides.",
  ],
  [
    "Business Failure Simulator",
    "Red Team and Risk model 7-, 30-, 90-, and 365-day failure horizons.",
  ],
  [
    "Red Team Agent",
    "Surfaces the weakest assumption, evidence needed, severity, fix, and revised recommendation.",
  ],
  [
    "Synthetic Customer Interviews",
    "Twenty explicitly synthetic personas across 13 fields, followed by a validation-focused synthesis.",
  ],
  [
    "Founder Clone File",
    "Sixteen founder-profile fields shape every venture brief without training a model.",
  ],
  [
    "Memory System",
    "Sixteen governed categories, per-agent write rules, workflow autosaves, API, and UI browser.",
  ],
  [
    "Business Playbook Library",
    "Twelve business-model playbooks are served by the API and available in Venture Studio.",
  ],
  [
    "Idea Scoring Engine",
    "Fourteen category scores feed code-computed Go, No-Go, or Test-First verdicts.",
  ],
  [
    "Execution Dashboard Schema",
    "Sixteen operating entities map into one command surface for reports, tasks, and decisions.",
  ],
] as const;

const RUN_MODES: ReadonlyArray<{
  title: string;
  copy: string;
  href: string;
  linkLabel: string;
  icon: LucideIcon;
}> = [
  {
    title: "Demo mode",
    copy: "Run the full agent flow locally with rule-based reasoning and real tools, with no model API spend.",
    href: `${REPO_URL}/tree/${DOCS_REVISION}#quick-start`,
    linkLabel: "Read the quick start",
    icon: SquareTerminal,
  },
  {
    title: "Free LLM",
    copy: "Connect a free-tier compatible model through the documented local proxy when you want live reasoning.",
    href: `${REPO_URL}/blob/${DOCS_REVISION}/docs/FREE_LLM_SETUP.md`,
    linkLabel: "Open the setup guide",
    icon: GitBranch,
  },
  {
    title: "Your data",
    copy: "Validate canonical CSV exports before replacing demo data. Reports and other artifacts stay intact.",
    href: `${REPO_URL}/blob/${DOCS_REVISION}/docs/CONNECT_REAL_BUSINESS.md`,
    linkLabel: "See the import contract",
    icon: Database,
  },
];

function SectionHeading({
  id,
  eyebrow,
  title,
  copy,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  copy: string;
}) {
  return (
    <div className="max-w-2xl">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
        {eyebrow}
      </p>
      <h2
        id={id}
        className="mt-3 text-balance text-3xl font-semibold tracking-tight text-slate-50 sm:text-4xl"
      >
        {title}
      </h2>
      <p className="mt-4 text-pretty text-base leading-7 text-slate-400 sm:text-lg">{copy}</p>
    </div>
  );
}

function AskIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 240 120" fill="none" aria-hidden="true" {...props}>
      <rect x="18" y="24" width="84" height="72" rx="12" stroke="#a78bfa" strokeOpacity=".65" />
      <path d="M34 45h48M34 58h34M34 71h42" stroke="#cbd5e1" strokeOpacity=".55" strokeLinecap="round" />
      <path d="M102 60h34" stroke="#a78bfa" strokeOpacity=".65" />
      <circle cx="151" cy="60" r="14" fill="#a78bfa" fillOpacity=".18" stroke="#a78bfa" />
      <path d="M165 53 199 34M165 67l34 19" stroke="#22d3ee" strokeOpacity=".45" />
      <circle cx="207" cy="30" r="8" fill="#22d3ee" fillOpacity=".18" stroke="#22d3ee" />
      <circle cx="207" cy="90" r="8" fill="#f472b6" fillOpacity=".16" stroke="#f472b6" />
    </svg>
  );
}

function DecideIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 240 120" fill="none" aria-hidden="true" {...props}>
      <path d="m120 14 25 14v28l-25 14-25-14V28l25-14Z" fill="#a78bfa" fillOpacity=".16" stroke="#a78bfa" />
      <path d="M95 42H54m91 0h41M104 63 76 87m60-24 28 24" stroke="#64748b" strokeOpacity=".55" />
      <circle cx="45" cy="42" r="10" stroke="#34d399" />
      <circle cx="195" cy="42" r="10" stroke="#f472b6" />
      <circle cx="68" cy="94" r="10" stroke="#38bdf8" />
      <circle cx="172" cy="94" r="10" stroke="#f87171" />
      <path d="m113 42 5 5 10-12" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function OperateIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 240 120" fill="none" aria-hidden="true" {...props}>
      <rect x="24" y="18" width="192" height="84" rx="12" stroke="#64748b" strokeOpacity=".65" />
      <path d="M24 42h192M82 42v60" stroke="#64748b" strokeOpacity=".45" />
      <circle cx="42" cy="30" r="3" fill="#a78bfa" />
      <circle cx="52" cy="30" r="3" fill="#22d3ee" fillOpacity=".75" />
      <path d="M39 57h28M39 69h20M39 81h25" stroke="#94a3b8" strokeLinecap="round" />
      <rect x="98" y="58" width="45" height="28" rx="6" fill="#a78bfa" fillOpacity=".12" stroke="#a78bfa" strokeOpacity=".6" />
      <path d="m109 72 6 6 13-14" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M158 61h36M158 72h29M158 83h33" stroke="#cbd5e1" strokeOpacity=".55" strokeLinecap="round" />
    </svg>
  );
}

const HOW_STEPS = [
  {
    number: "01",
    title: "Ask",
    copy: "Chat with the CEO. It routes the request, delegates specialist work in parallel, and shows the live decision tree.",
    Illustration: AskIllustration,
  },
  {
    number: "02",
    title: "Decide",
    copy: "Run a board debate, score an idea, or simulate failure. Deterministic code owns the final gates and saved artifacts.",
    Illustration: DecideIllustration,
  },
  {
    number: "03",
    title: "Operate",
    copy: "Use reports, approval controls, business memory, and task coordination to turn a decision into accountable work.",
    Illustration: OperateIllustration,
  },
] as const;

export default function MarketingPage() {
  return (
    <>
      <LandingHero />

      <section aria-labelledby="org-chart-title" className="border-b border-white/[0.06] bg-[#0d1422]">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
          <SectionHeading
            id="org-chart-title"
            eyebrow="The boardroom"
            title="Twenty-one agents, organized like a real company."
            copy="The landing roster mirrors the product roster exactly: an operations team for the running company, a CFO-led finance team, and a separate venture team for founder workflows."
          />
          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {AGENT_TEAMS.map((team) => (
              <div key={team.name} className="rounded-2xl border border-white/[0.06] bg-white/[0.025] p-5">
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-slate-100">{team.name}</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-400">{team.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {team.agents.map(([name, color]) => (
                    <span
                      key={name}
                      className="inline-flex min-h-8 items-center gap-2 rounded-full border border-white/[0.07] bg-[#0a0f1a]/70 px-3 text-xs text-slate-300"
                    >
                      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} aria-hidden="true" />
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="scroll-mt-20 border-b border-white/[0.06] bg-[#0a0f1a]">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <SectionHeading
            eyebrow="How it works"
            title="Ask once. See the work. Keep the decision."
            copy="The model handles judgment. Deterministic application code handles routing, limits, persistence, and the final business rules."
          />
          <div className="mt-12 grid gap-5 lg:grid-cols-3">
            {HOW_STEPS.map(({ number, title, copy, Illustration }) => (
              <article key={title} className="rounded-2xl border border-white/[0.06] bg-[#101827]/60 p-6">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-violet-300">{number}</span>
                  <span className="h-px w-12 bg-gradient-to-r from-transparent to-violet-400/50" aria-hidden="true" />
                </div>
                <Illustration className="mt-4 h-28 w-full" />
                <h3 className="mt-5 text-xl font-semibold tracking-tight text-slate-100">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="systems" className="scroll-mt-20 border-b border-white/[0.06] bg-[#0d1422]">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <SectionHeading
            eyebrow="Twelve operating systems"
            title="More than a chat window."
            copy="Each system has a concrete code path, data contract, or verification gate in the repository."
          />
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SYSTEMS.map(([title, copy], index) => (
              <article
                key={title}
                className="group rounded-xl border border-white/[0.06] bg-[#0a0f1a]/55 p-5 transition duration-200 hover:-translate-y-1 hover:border-violet-400/35 motion-reduce:transform-none motion-reduce:transition-none"
              >
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 font-mono text-[11px] text-violet-300/80">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold leading-6 text-slate-100">{title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{copy}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden border-b border-white/[0.06] bg-[#0a0f1a]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_50%,rgba(167,139,250,0.09),transparent_34%)]" aria-hidden="true" />
        <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 sm:py-24 lg:grid-cols-[1fr,0.9fr] lg:items-center lg:px-8">
          <SectionHeading
            eyebrow="Model resilience"
            title="Built to survive model downgrades."
            copy="If you move to a smaller model, role survival guides restore structure. Deterministic verdicts keep final gates in code, and the evaluation harness shows where quality changed before that change reaches the business."
          />
          <dl className="grid grid-cols-3 gap-3">
            {[
              ["168", "backend tests"],
              ["18", "eval scenarios"],
              ["5", "deterministic workflows"],
            ].map(([value, label]) => (
              <div key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
                <dt className="text-xs leading-5 text-slate-400">{label}</dt>
                <dd className="mt-2 text-2xl font-semibold tracking-tight text-slate-100 sm:text-3xl">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="bg-[#0d1422]">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <SectionHeading
            eyebrow="Run it your way"
            title="Start with the mode you can support today."
            copy="The repository includes a no-spend demo, a documented proxy path, and a validated CSV importer for real business data."
          />
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {RUN_MODES.map(({ title, copy, href, linkLabel, icon: Icon }) => (
              <article key={title} className="flex min-h-64 flex-col rounded-2xl border border-white/[0.06] bg-[#0a0f1a]/60 p-6">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-violet-400/20 bg-violet-400/[0.08] text-violet-300">
                  <Icon size={20} aria-hidden={true} />
                </div>
                <h3 className="mt-5 text-lg font-semibold tracking-tight text-slate-100">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{copy}</p>
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-auto inline-flex min-h-11 items-center gap-1.5 rounded-lg pt-5 text-sm font-medium text-violet-300 transition-colors hover:text-violet-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 motion-reduce:transition-none"
                >
                  {linkLabel} <ArrowUpRight size={14} aria-hidden="true" />
                </a>
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
