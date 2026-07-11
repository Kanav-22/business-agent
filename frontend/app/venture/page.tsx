"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import {
  Archive,
  BookOpen,
  CheckCircle2,
  CircleAlert,
  ClipboardList,
  FlaskConical,
  Gauge,
  GitBranch,
  Loader2,
  MessageSquareText,
  Play,
  Rocket,
  Route as RouteIcon,
  Save,
  ShieldAlert,
  UserRound,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { Markdown } from "@/components/markdown";
import { API_BASE, getJson } from "@/lib/api";
import type {
  EvalRow,
  FounderProfile,
  FounderProfileKey,
  IdeaDetail,
  IdeaSummary,
  Memory as VentureMemory,
  Playbook,
  PlaybookSummary,
  ReportSummary,
  RouteDecision,
  VentureWorkflow,
} from "@/lib/types";

const POLL_MS = 3000;
const MAX_POLL_ATTEMPTS = 40;

const FIELD_CLASS =
  "min-h-11 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-base text-slate-100 outline-none transition-colors placeholder:text-slate-600 focus:border-violet-500 focus-visible:ring-2 focus-visible:ring-violet-400/70 disabled:cursor-not-allowed disabled:opacity-50";
const BUTTON_FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950";

const MEMORY_CATEGORIES = [
  "founder_profile",
  "business_idea",
  "active_business",
  "decision",
  "rejected_idea",
  "customer_research",
  "competitor_research",
  "financial_assumption",
  "product_roadmap",
  "marketing_experiment",
  "sales_conversation",
  "metric",
  "risk",
  "lesson_learned",
  "board_meeting",
  "agent_performance",
] as const;

const FOUNDER_FIELDS: ReadonlyArray<{
  key: FounderProfileKey;
  label: string;
  helper: string;
}> = [
  { key: "skills", label: "Skills", helper: "What you are genuinely good at, with evidence." },
  { key: "weaknesses", label: "Weaknesses", helper: "What you are bad at or tend to avoid." },
  { key: "working_style", label: "Working style", helper: "How you actually work best." },
  { key: "risk_tolerance", label: "Risk tolerance", helper: "Low, medium, or high, and what that means for you." },
  { key: "budget_range", label: "Budget range", helper: "Capital actually available for the next venture." },
  { key: "long_term_goals", label: "Long-term goals", helper: "Where this should lead in three to five years." },
  { key: "current_assets", label: "Current assets", helper: "Audience, network, tools, intellectual property, or other leverage." },
  { key: "coding_ability", label: "Coding ability", helper: "Your honest level so agents can scope realistic MVPs." },
  { key: "business_interests", label: "Business interests", helper: "Domains that consistently hold your attention." },
  { key: "communication_style", label: "Communication style", helper: "How you want agents to communicate with you." },
  { key: "decision_flaws", label: "Decision flaws", helper: "Your known failure modes when making decisions." },
  { key: "how_to_challenge", label: "How to challenge", helper: "What agents should push back on, and how." },
  { key: "how_to_focus", label: "How to focus", helper: "What reliably keeps you committed to one thing." },
  { key: "distracting_ideas", label: "Distracting ideas", helper: "The shiny ideas that repeatedly derail you." },
  { key: "avoid", label: "Avoid", helper: "Hard constraints agents should never recommend." },
  { key: "double_down", label: "Double down", helper: "Where past evidence says you should lean in." },
];

const EMPTY_PROFILE: FounderProfile = {
  skills: "",
  weaknesses: "",
  working_style: "",
  risk_tolerance: "",
  budget_range: "",
  long_term_goals: "",
  current_assets: "",
  coding_ability: "",
  business_interests: "",
  communication_style: "",
  decision_flaws: "",
  how_to_challenge: "",
  how_to_focus: "",
  distracting_ideas: "",
  avoid: "",
  double_down: "",
};

const WORKFLOW_ICONS: Record<string, LucideIcon> = {
  debate: MessageSquareText,
  failure_sim: ShieldAlert,
  interviews: UsersRound,
  idea_score: Gauge,
};

const VERDICT_META: Record<IdeaSummary["verdict"], { label: string; className: string }> = {
  go: { label: "Go", className: "border-emerald-800 bg-emerald-950/50 text-emerald-300" },
  test_first: { label: "Test first", className: "border-amber-800 bg-amber-950/50 text-amber-300" },
  no_go: { label: "No-go", className: "border-red-800 bg-red-950/50 text-red-300" },
};

const RISK_META: Record<RouteDecision["risk_level"], string> = {
  low: "border-emerald-800 bg-emerald-950/50 text-emerald-300",
  medium: "border-amber-800 bg-amber-950/50 text-amber-300",
  high: "border-red-800 bg-red-950/50 text-red-300",
};

type WorkflowPhase = "starting" | "polling" | "success" | "error";
type WorkflowState = { phase: WorkflowPhase; message?: string };

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string, includeTime = false): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unknown date";
  return includeTime ? parsed.toLocaleString() : parsed.toLocaleDateString();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function apiError(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // The fallback includes enough context when an upstream returns no JSON body.
  }
  return `${fallback} (HTTP ${response.status})`;
}

async function sendJson<T>(
  path: string,
  method: "POST" | "PUT",
  body?: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(await apiError(response, `Request to ${path} failed`));
  return response.json();
}

function Section({
  id,
  title,
  description,
  icon: Icon,
  children,
}: {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="scroll-mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 sm:p-6"
    >
      <div className="mb-5 flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-violet-800/70 bg-violet-950/40 text-violet-300">
          <Icon size={20} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h2 id={`${id}-title`} className="text-base font-semibold text-slate-100">
            {title}
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-400">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex min-h-24 items-center justify-center gap-2 text-sm text-slate-400" role="status">
      <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
      {label}
    </div>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm leading-relaxed text-slate-400">
      {children}
    </div>
  );
}

function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="rounded-xl border border-red-900/70 bg-red-950/30 p-4" role="alert">
      <div className="flex items-start gap-2 text-sm text-red-200">
        <CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span className="min-w-0 break-words">{message}</span>
      </div>
      <button
        type="button"
        onClick={retry}
        className={clsx(
          "mt-3 min-h-11 rounded-lg border border-red-800 px-4 text-sm font-medium text-red-200 transition-colors hover:bg-red-900/30",
          BUTTON_FOCUS,
        )}
      >
        Try again
      </button>
    </div>
  );
}

export default function VentureStudioPage() {
  const mountedRef = useRef(true);
  const ideaRequestRef = useRef(0);
  const memoryRequestRef = useRef(0);
  const playbookRequestRef = useRef(0);
  const [workflows, setWorkflows] = useState<VentureWorkflow[] | null>(null);
  const [workflowsError, setWorkflowsError] = useState<string | null>(null);
  const [workflowTopic, setWorkflowTopic] = useState("");
  const [workflowTopicError, setWorkflowTopicError] = useState<string | null>(null);
  const [workflowStates, setWorkflowStates] = useState<Record<string, WorkflowState>>({});
  const [workflowReports, setWorkflowReports] = useState<Record<string, ReportSummary>>({});

  const [ideas, setIdeas] = useState<IdeaSummary[] | null>(null);
  const [ideasError, setIdeasError] = useState<string | null>(null);
  const [expandedIdeaId, setExpandedIdeaId] = useState<number | null>(null);
  const [ideaDetail, setIdeaDetail] = useState<IdeaDetail | null>(null);
  const [ideaDetailLoading, setIdeaDetailLoading] = useState(false);
  const [ideaDetailError, setIdeaDetailError] = useState<string | null>(null);

  const [routerMessage, setRouterMessage] = useState("");
  const [routeDecision, setRouteDecision] = useState<RouteDecision | null>(null);
  const [routerState, setRouterState] = useState<"idle" | "loading" | "error">("idle");
  const [routerError, setRouterError] = useState<string | null>(null);

  const [profile, setProfile] = useState<FounderProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileNotice, setProfileNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  const [memoryCategory, setMemoryCategory] = useState("");
  const [memories, setMemories] = useState<VentureMemory[] | null>(null);
  const [memoriesError, setMemoriesError] = useState<string | null>(null);
  const [archivingMemory, setArchivingMemory] = useState<number | null>(null);

  const [playbooks, setPlaybooks] = useState<PlaybookSummary[] | null>(null);
  const [playbooksError, setPlaybooksError] = useState<string | null>(null);
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [playbookLoading, setPlaybookLoading] = useState<string | null>(null);
  const [playbookError, setPlaybookError] = useState<string | null>(null);

  const [evals, setEvals] = useState<EvalRow[] | null>(null);
  const [evalsError, setEvalsError] = useState<string | null>(null);

  const loadWorkflows = useCallback(() => {
    setWorkflows(null);
    setWorkflowsError(null);
    getJson<VentureWorkflow[]>("/api/venture/workflows")
      .then(setWorkflows)
      .catch((error) => setWorkflowsError(`Could not load workflows: ${String(error)}`));
  }, []);

  const loadIdeas = useCallback(() => {
    setIdeas(null);
    setIdeasError(null);
    getJson<IdeaSummary[]>("/api/ideas")
      .then(setIdeas)
      .catch((error) => setIdeasError(`Could not load ideas: ${String(error)}`));
  }, []);

  const loadProfile = useCallback(() => {
    setProfile(null);
    setProfileError(null);
    getJson<FounderProfile>("/api/founder")
      .then((values) => setProfile({ ...EMPTY_PROFILE, ...values }))
      .catch((error) => setProfileError(`Could not load the founder profile: ${String(error)}`));
  }, []);

  const loadMemories = useCallback(() => {
    const requestId = ++memoryRequestRef.current;
    setMemories(null);
    setMemoriesError(null);
    const query = memoryCategory ? `&category=${encodeURIComponent(memoryCategory)}` : "";
    getJson<VentureMemory[]>(`/api/memories?status=active${query}`)
      .then((records) => {
        if (memoryRequestRef.current === requestId) setMemories(records);
      })
      .catch((error) => {
        if (memoryRequestRef.current === requestId) {
          setMemoriesError(`Could not load memories: ${String(error)}`);
        }
      });
  }, [memoryCategory]);

  const loadPlaybooks = useCallback(() => {
    setPlaybooks(null);
    setPlaybooksError(null);
    getJson<PlaybookSummary[]>("/api/playbooks")
      .then(setPlaybooks)
      .catch((error) => setPlaybooksError(`Could not load playbooks: ${String(error)}`));
  }, []);

  const loadEvals = useCallback(() => {
    setEvals(null);
    setEvalsError(null);
    getJson<EvalRow[]>("/api/evals")
      .then(setEvals)
      .catch((error) => setEvalsError(`Could not load evaluation runs: ${String(error)}`));
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    loadWorkflows();
    loadIdeas();
    loadProfile();
    loadPlaybooks();
    loadEvals();
    return () => {
      mountedRef.current = false;
    };
  }, [loadEvals, loadIdeas, loadPlaybooks, loadProfile, loadWorkflows]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  const profileIsEmpty = useMemo(
    () => profile !== null && Object.values(profile).every((value) => !value.trim()),
    [profile],
  );

  const updateWorkflowState = (name: string, state: WorkflowState) => {
    if (!mountedRef.current) return;
    setWorkflowStates((current) => ({ ...current, [name]: state }));
  };

  const pollForReport = async (workflowName: string, startedAt: number) => {
    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
      if (attempt > 0) await sleep(POLL_MS);
      if (!mountedRef.current) return;
      const reports = await getJson<ReportSummary[]>(
        `/api/reports?kind=${encodeURIComponent(workflowName)}&limit=1`,
      );
      const latest = reports[0];
      if (latest && new Date(latest.created_at).getTime() > startedAt) {
        setWorkflowReports((current) => ({ ...current, [workflowName]: latest }));
        updateWorkflowState(workflowName, {
          phase: "success",
          message: "New report is ready.",
        });
        if (workflowName === "idea_score") loadIdeas();
        return;
      }
    }
    throw new Error("No new report appeared within two minutes. Check the backend logs, then try again.");
  };

  const runWorkflow = async (workflow: VentureWorkflow) => {
    const topic = workflowTopic.trim();
    if (!topic) {
      setWorkflowTopicError("Enter a business idea or decision topic before running a workflow.");
      return;
    }
    if (topic.length > 500) {
      setWorkflowTopicError("Keep the topic to 500 characters or fewer.");
      return;
    }
    setWorkflowTopicError(null);
    setWorkflowReports((current) => {
      const next = { ...current };
      delete next[workflow.name];
      return next;
    });
    updateWorkflowState(workflow.name, { phase: "starting", message: "Starting workflow…" });
    const startedAt = Date.now();
    try {
      await sendJson<{ started: boolean; workflow: string }>(
        `/api/venture/${encodeURIComponent(workflow.name)}`,
        "POST",
        { topic },
      );
      updateWorkflowState(workflow.name, {
        phase: "polling",
        message: "Agents are working. Waiting for the report…",
      });
      await pollForReport(workflow.name, startedAt);
    } catch (error) {
      updateWorkflowState(workflow.name, {
        phase: "error",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  };

  const toggleIdea = async (ideaId: number) => {
    const requestId = ++ideaRequestRef.current;
    if (expandedIdeaId === ideaId) {
      setExpandedIdeaId(null);
      setIdeaDetail(null);
      setIdeaDetailError(null);
      setIdeaDetailLoading(false);
      return;
    }
    setExpandedIdeaId(ideaId);
    setIdeaDetail(null);
    setIdeaDetailLoading(true);
    setIdeaDetailError(null);
    try {
      const detail = await getJson<IdeaDetail>(`/api/ideas/${ideaId}`);
      if (ideaRequestRef.current === requestId) setIdeaDetail(detail);
    } catch (error) {
      if (ideaRequestRef.current === requestId) {
        setIdeaDetailError(`Could not load this idea: ${String(error)}`);
      }
    } finally {
      if (ideaRequestRef.current === requestId) setIdeaDetailLoading(false);
    }
  };

  const routeRequest = async (event: React.FormEvent) => {
    event.preventDefault();
    const message = routerMessage.trim();
    if (!message) {
      setRouterState("error");
      setRouterError("Enter a request for the router to classify.");
      return;
    }
    setRouterState("loading");
    setRouterError(null);
    setRouteDecision(null);
    try {
      setRouteDecision(await sendJson<RouteDecision>("/api/route", "POST", { message }));
      setRouterState("idle");
    } catch (error) {
      setRouterState("error");
      setRouterError(error instanceof Error ? error.message : String(error));
    }
  };

  const saveProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!profile) return;
    const values = Object.fromEntries(
      Object.entries(profile)
        .filter(([, value]) => value.trim())
        .map(([key, value]) => [key, value.trim()]),
    );
    if (Object.keys(values).length === 0) {
      setProfileNotice({ kind: "error", text: "Add at least one profile value before saving." });
      return;
    }
    setProfileSaving(true);
    setProfileNotice(null);
    try {
      const saved = await sendJson<FounderProfile>("/api/founder", "PUT", { values });
      setProfile({ ...EMPTY_PROFILE, ...saved });
      setProfileNotice({ kind: "success", text: "Founder profile saved. New venture work will use it." });
    } catch (error) {
      setProfileNotice({
        kind: "error",
        text: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setProfileSaving(false);
    }
  };

  const archiveMemory = async (memory: VentureMemory) => {
    if (!window.confirm(`Archive “${memory.title}”? It will leave the active-memory view.`)) return;
    setArchivingMemory(memory.id);
    setMemoriesError(null);
    try {
      await sendJson<{ archived: boolean; id: number }>(`/api/memories/${memory.id}/archive`, "POST");
      setMemories((current) => current?.filter((item) => item.id !== memory.id) ?? []);
    } catch (error) {
      setMemoriesError(`Could not archive “${memory.title}”: ${String(error)}`);
    } finally {
      setArchivingMemory(null);
    }
  };

  const openPlaybook = async (summary: PlaybookSummary) => {
    const requestId = ++playbookRequestRef.current;
    setPlaybookLoading(summary.slug);
    setPlaybookError(null);
    try {
      const playbook = await getJson<Playbook>(
        `/api/playbooks/${encodeURIComponent(summary.slug)}`,
      );
      if (playbookRequestRef.current === requestId) setSelectedPlaybook(playbook);
    } catch (error) {
      if (playbookRequestRef.current === requestId) {
        setPlaybookError(`Could not open “${summary.title}”: ${String(error)}`);
      }
    } finally {
      if (playbookRequestRef.current === requestId) setPlaybookLoading(null);
    }
  };

  return (
    <div className="min-w-0 overflow-x-hidden">
      <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
        <header className="relative overflow-hidden rounded-2xl border border-violet-900/60 bg-gradient-to-br from-violet-950/70 via-slate-900 to-slate-950 p-5 sm:p-8">
          <div className="absolute -right-16 -top-20 h-56 w-56 rounded-full bg-violet-500/10 blur-3xl" aria-hidden="true" />
          <div className="relative flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-violet-700/60 bg-violet-500/15 text-violet-300">
              <Rocket size={23} aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-violet-300">Venture layer</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">Venture Studio</h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-300 sm:text-base">
                Pressure-test ideas, route high-stakes decisions, and keep founder context in one operating surface.
              </p>
            </div>
          </div>
        </header>

        <Section
          id="workflows"
          title="Run a workflow"
          description="Give the venture team one concrete topic, then choose the type of pressure test you need."
          icon={FlaskConical}
        >
          <div>
            <label htmlFor="workflow-topic" className="text-sm font-medium text-slate-200">
              Business idea or decision topic
            </label>
            <input
              id="workflow-topic"
              value={workflowTopic}
              onChange={(event) => {
                setWorkflowTopic(event.target.value);
                if (workflowTopicError) setWorkflowTopicError(null);
              }}
              maxLength={500}
              placeholder="Example: Should I build an AI appointment assistant for independent clinics?"
              className={clsx(FIELD_CLASS, "mt-2")}
              aria-describedby="workflow-topic-hint workflow-topic-error"
              aria-invalid={Boolean(workflowTopicError)}
            />
            <div className="mt-2 flex flex-wrap items-start justify-between gap-2 text-xs text-slate-500">
              <p id="workflow-topic-hint">With DEMO_MODE=1, reasoning is canned but tools and saved results are real.</p>
              <span className="tabular-nums">{workflowTopic.length}/500</span>
            </div>
            {workflowTopicError && (
              <p id="workflow-topic-error" className="mt-2 text-sm text-red-300" role="alert">
                {workflowTopicError}
              </p>
            )}
          </div>

          <div className="mt-5">
            {workflowsError ? (
              <ErrorState message={workflowsError} retry={loadWorkflows} />
            ) : workflows === null ? (
              <LoadingState label="Loading venture workflows…" />
            ) : workflows.length === 0 ? (
              <EmptyState>No venture workflows are registered yet. Check the backend configuration.</EmptyState>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {workflows.map((workflow) => {
                  const state = workflowStates[workflow.name];
                  const report = workflowReports[workflow.name];
                  const running = state?.phase === "starting" || state?.phase === "polling";
                  const Icon = WORKFLOW_ICONS[workflow.name] ?? Play;
                  return (
                    <div key={workflow.name} className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <div className="flex items-start gap-3">
                        <Icon size={18} className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
                        <div className="min-w-0">
                          <h3 className="text-sm font-semibold text-slate-200">{workflow.label}</h3>
                          <p className="mt-1 text-xs leading-relaxed text-slate-500">{workflow.description}</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => void runWorkflow(workflow)}
                        disabled={running}
                        className={clsx(
                          "mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-violet-800 bg-violet-950/40 px-4 text-sm font-medium text-violet-200 transition-colors hover:border-violet-600 hover:bg-violet-900/40 disabled:cursor-wait disabled:opacity-50",
                          BUTTON_FOCUS,
                        )}
                      >
                        {running ? (
                          <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
                        ) : (
                          <Play size={16} aria-hidden="true" />
                        )}
                        {state?.phase === "starting"
                          ? "Starting…"
                          : state?.phase === "polling"
                            ? "Waiting for report…"
                            : `Run ${workflow.label}`}
                      </button>
                      {state && (
                        <div
                          className={clsx(
                            "mt-3 rounded-lg border p-3 text-xs leading-relaxed",
                            state.phase === "error"
                              ? "border-red-900/70 bg-red-950/30 text-red-200"
                              : state.phase === "success"
                                ? "border-emerald-900/70 bg-emerald-950/30 text-emerald-200"
                                : "border-slate-800 bg-slate-900/70 text-slate-400",
                          )}
                          role={state.phase === "error" ? "alert" : "status"}
                          aria-live="polite"
                        >
                          {state.message}
                        </div>
                      )}
                      {report && (
                        <div className="mt-3 min-w-0 rounded-lg border border-emerald-900/70 bg-emerald-950/20 p-3">
                          <div className="flex items-start gap-2">
                            <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-400" aria-hidden="true" />
                            <div className="min-w-0">
                              <p className="break-words text-sm font-medium text-slate-200">{report.title}</p>
                              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">{report.excerpt}</p>
                              <Link
                                href="/reports"
                                className={clsx(
                                  "mt-2 inline-flex min-h-11 items-center gap-1.5 rounded-lg px-1 text-sm font-medium text-emerald-300 hover:text-emerald-200",
                                  BUTTON_FOCUS,
                                )}
                              >
                                Open in Reports
                                <span aria-hidden="true">→</span>
                              </Link>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Section>

        <Section
          id="ideas"
          title="Idea scoreboard"
          description="Compare scored ideas and expand a row to inspect the rationale, risk, and next validation step."
          icon={Gauge}
        >
          {ideasError ? (
            <ErrorState message={ideasError} retry={loadIdeas} />
          ) : ideas === null ? (
            <LoadingState label="Loading scored ideas…" />
          ) : ideas.length === 0 ? (
            <EmptyState>No ideas have been scored yet. Run Idea score above to create the first verdict.</EmptyState>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full table-fixed text-left text-sm">
                <thead className="bg-slate-950/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="w-[48%] px-3 py-3 font-medium sm:w-auto sm:px-4">Idea</th>
                    <th className="w-[20%] px-2 py-3 font-medium sm:w-24">Total</th>
                    <th className="w-[32%] px-2 py-3 font-medium sm:w-32">Verdict</th>
                    <th className="hidden px-4 py-3 font-medium sm:table-cell sm:w-32">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {ideas.map((idea) => {
                    const expanded = expandedIdeaId === idea.id;
                    const verdict = VERDICT_META[idea.verdict];
                    return (
                      <IdeaRows
                        key={idea.id}
                        idea={idea}
                        expanded={expanded}
                        verdict={verdict}
                        onToggle={() => void toggleIdea(idea.id)}
                        detail={expanded ? ideaDetail : null}
                        loading={expanded && ideaDetailLoading}
                        error={expanded ? ideaDetailError : null}
                      />
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section
          id="router"
          title="Router tester"
          description="See which agent, supporting team, workflow, and risk controls a request would trigger."
          icon={RouteIcon}
        >
          <form onSubmit={routeRequest}>
            <label htmlFor="router-message" className="text-sm font-medium text-slate-200">
              Request to route
            </label>
            <textarea
              id="router-message"
              value={routerMessage}
              onChange={(event) => {
                setRouterMessage(event.target.value);
                if (routerError) setRouterError(null);
              }}
              rows={3}
              placeholder="Example: I want to launch an AI tool for doctors."
              className={clsx(FIELD_CLASS, "mt-2 resize-y")}
              aria-invalid={Boolean(routerError)}
              aria-describedby={routerError ? "router-error" : undefined}
            />
            <button
              type="submit"
              disabled={routerState === "loading"}
              className={clsx(
                "mt-3 flex min-h-11 items-center justify-center gap-2 rounded-lg bg-violet-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:cursor-wait disabled:opacity-50",
                BUTTON_FOCUS,
              )}
            >
              {routerState === "loading" ? (
                <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
              ) : (
                <GitBranch size={16} aria-hidden="true" />
              )}
              {routerState === "loading" ? "Routing…" : "Route request"}
            </button>
          </form>

          {routerError && (
            <div id="router-error" className="mt-4 rounded-lg border border-red-900/70 bg-red-950/30 p-3 text-sm text-red-200" role="alert">
              {routerError}
            </div>
          )}

          {routeDecision && (
            <div className="mt-5 space-y-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:p-5" aria-live="polite">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded border border-violet-800 bg-violet-950/50 px-2 py-1 text-xs font-medium text-violet-300">
                  {humanize(routeDecision.category)}
                </span>
                <span className={clsx("rounded border px-2 py-1 text-xs font-semibold uppercase", RISK_META[routeDecision.risk_level])}>
                  {routeDecision.risk_level} risk
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Primary agent</h3>
                  <p className="mt-1 text-sm font-semibold text-slate-100">{humanize(routeDecision.primary_agent)}</p>
                </div>
                <div>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Supporting agents</h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {routeDecision.supporting_agents.length ? (
                      routeDecision.supporting_agents.map((agent) => (
                        <span key={agent} className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-300">
                          {humanize(agent)}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">No supporting agents required.</span>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Workflow</h3>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-300">
                  {routeDecision.workflow.map((step, index) => (
                    <span key={`${step}-${index}`} className="flex items-center gap-2">
                      {index > 0 && <span className="text-slate-600" aria-hidden="true">→</span>}
                      <span className="rounded border border-slate-700 bg-slate-900 px-2.5 py-1">{humanize(step)}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Why this route</h3>
                  <p className="mt-1 text-sm leading-relaxed text-slate-300">{routeDecision.reason}</p>
                </div>
                <div>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Expected output</h3>
                  <p className="mt-1 text-sm leading-relaxed text-slate-300">{routeDecision.expected_output}</p>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Required inputs</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
                  {routeDecision.required_inputs.map((input) => <li key={input}>{input}</li>)}
                </ul>
              </div>

              {routeDecision.founder_fit_note && (
                <div className="rounded-lg border border-sky-900/70 bg-sky-950/30 p-3 text-sm leading-relaxed text-sky-200">
                  <span className="font-semibold">Founder fit:</span> {routeDecision.founder_fit_note}
                </div>
              )}
              {routeDecision.warnings.map((warning) => (
                <div key={warning} className="flex items-start gap-2 rounded-lg border border-amber-900/70 bg-amber-950/30 p-3 text-sm leading-relaxed text-amber-200">
                  <CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
                  {warning}
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section
          id="founder-profile"
          title="Founder profile"
          description="Give every venture recommendation the same honest context about your abilities, constraints, and failure modes."
          icon={UserRound}
        >
          {profileError ? (
            <ErrorState message={profileError} retry={loadProfile} />
          ) : profile === null ? (
            <LoadingState label="Loading founder profile…" />
          ) : (
            <form onSubmit={saveProfile}>
              {profileIsEmpty && (
                <div className="mb-4 rounded-lg border border-amber-900/60 bg-amber-950/20 p-3 text-sm text-amber-200">
                  Your profile is unset. Add the fields you know now; you can return to complete the rest.
                </div>
              )}
              <div className="grid gap-4 lg:grid-cols-2">
                {FOUNDER_FIELDS.map((field) => (
                  <div key={field.key} className="min-w-0">
                    <label htmlFor={`founder-${field.key}`} className="text-sm font-medium text-slate-200">
                      {field.label}
                    </label>
                    <textarea
                      id={`founder-${field.key}`}
                      value={profile[field.key]}
                      onChange={(event) => setProfile((current) => current ? { ...current, [field.key]: event.target.value } : current)}
                      rows={3}
                      maxLength={1500}
                      className={clsx(FIELD_CLASS, "mt-2 resize-y")}
                      aria-describedby={`founder-${field.key}-help`}
                    />
                    <p id={`founder-${field.key}-help`} className="mt-1.5 text-xs leading-relaxed text-slate-500">
                      {field.helper}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  disabled={profileSaving}
                  className={clsx(
                    "flex min-h-11 items-center justify-center gap-2 rounded-lg bg-violet-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:cursor-wait disabled:opacity-50",
                    BUTTON_FOCUS,
                  )}
                >
                  {profileSaving ? (
                    <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
                  ) : (
                    <Save size={16} aria-hidden="true" />
                  )}
                  {profileSaving ? "Saving…" : "Save profile"}
                </button>
                {profileNotice && (
                  <div
                    className={clsx(
                      "rounded-lg border px-3 py-2 text-sm",
                      profileNotice.kind === "success"
                        ? "border-emerald-900/70 bg-emerald-950/30 text-emerald-200"
                        : "border-red-900/70 bg-red-950/30 text-red-200",
                    )}
                    role={profileNotice.kind === "error" ? "alert" : "status"}
                    aria-live="polite"
                  >
                    {profileNotice.text}
                  </div>
                )}
              </div>
            </form>
          )}
        </Section>

        <Section
          id="memories"
          title="Memories"
          description="Browse the active evidence, decisions, and lessons that agents carry into future venture work."
          icon={ClipboardList}
        >
          <div className="mb-4 max-w-sm">
            <label htmlFor="memory-category" className="text-sm font-medium text-slate-200">
              Category
            </label>
            <select
              id="memory-category"
              value={memoryCategory}
              onChange={(event) => setMemoryCategory(event.target.value)}
              className={clsx(FIELD_CLASS, "mt-2")}
            >
              <option value="">All categories</option>
              {MEMORY_CATEGORIES.map((category) => (
                <option key={category} value={category}>{humanize(category)}</option>
              ))}
            </select>
          </div>

          {memoriesError ? (
            <ErrorState message={memoriesError} retry={loadMemories} />
          ) : memories === null ? (
            <LoadingState label="Loading active memories…" />
          ) : memories.length === 0 ? (
            <EmptyState>
              No active {memoryCategory ? humanize(memoryCategory).toLowerCase() : "venture"} memories yet. Workflows will save useful evidence here.
            </EmptyState>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {memories.map((memory) => (
                <article key={memory.id} className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <span className="inline-flex rounded border border-sky-900 bg-sky-950/40 px-2 py-0.5 text-xs text-sky-300">
                        {humanize(memory.category)}
                      </span>
                      <h3 className="mt-2 break-words text-sm font-semibold text-slate-100">{memory.title}</h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => void archiveMemory(memory)}
                      disabled={archivingMemory === memory.id}
                      className={clsx(
                        "flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-slate-700 px-3 text-xs font-medium text-slate-300 transition-colors hover:border-amber-700 hover:text-amber-200 disabled:cursor-wait disabled:opacity-50",
                        BUTTON_FOCUS,
                      )}
                      aria-label={`Archive memory: ${memory.title}`}
                    >
                      {archivingMemory === memory.id ? (
                        <Loader2 size={14} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
                      ) : (
                        <Archive size={14} aria-hidden="true" />
                      )}
                      Archive
                    </button>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-300">{memory.content}</p>
                  <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 border-t border-slate-800 pt-3 text-xs text-slate-500">
                    <span>Source: {humanize(memory.source_agent)}</span>
                    <span>{formatDate(memory.created_at, true)}</span>
                    {memory.related_idea && <span>Idea: {memory.related_idea}</span>}
                  </div>
                </article>
              ))}
            </div>
          )}
        </Section>

        <Section
          id="playbooks"
          title="Playbooks"
          description="Open a repeatable operating guide without leaving the venture workspace."
          icon={BookOpen}
        >
          {playbooksError ? (
            <ErrorState message={playbooksError} retry={loadPlaybooks} />
          ) : playbooks === null ? (
            <LoadingState label="Loading business playbooks…" />
          ) : playbooks.length === 0 ? (
            <EmptyState>No playbooks are installed yet. Add markdown guides under docs/playbooks.</EmptyState>
          ) : (
            <div className="grid min-w-0 gap-4 lg:grid-cols-[260px,minmax(0,1fr)]">
              <div className="space-y-2">
                {playbooks.map((playbook) => (
                  <button
                    key={playbook.slug}
                    type="button"
                    onClick={() => void openPlaybook(playbook)}
                    disabled={playbookLoading === playbook.slug}
                    className={clsx(
                      "flex min-h-11 w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors disabled:cursor-wait disabled:opacity-60",
                      selectedPlaybook?.slug === playbook.slug
                        ? "border-violet-700 bg-violet-950/40 text-violet-200"
                        : "border-slate-800 bg-slate-950/50 text-slate-300 hover:border-slate-600",
                      BUTTON_FOCUS,
                    )}
                  >
                    {playbookLoading === playbook.slug ? (
                      <Loader2 size={15} className="shrink-0 animate-spin motion-reduce:animate-none" aria-hidden="true" />
                    ) : (
                      <BookOpen size={15} className="shrink-0" aria-hidden="true" />
                    )}
                    <span className="min-w-0 break-words">{playbook.title}</span>
                  </button>
                ))}
              </div>

              <div className="min-w-0">
                {playbookError ? (
                  <div className="rounded-xl border border-red-900/70 bg-red-950/30 p-4 text-sm text-red-200" role="alert">
                    {playbookError}
                  </div>
                ) : selectedPlaybook ? (
                  <div className="max-h-[36rem] min-w-0 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:p-6">
                    <Markdown>{selectedPlaybook.content}</Markdown>
                  </div>
                ) : (
                  <EmptyState>Select a playbook to read its operating steps.</EmptyState>
                )}
              </div>
            </div>
          )}
        </Section>

        <Section
          id="evaluations"
          title="Evaluation runs"
          description="Track deterministic output-quality scores across agents and model configurations."
          icon={CheckCircle2}
        >
          {evalsError ? (
            <ErrorState message={evalsError} retry={loadEvals} />
          ) : evals === null ? (
            <LoadingState label="Loading evaluation results…" />
          ) : evals.length === 0 ? (
            <EmptyState>
              No evaluation results yet. Run the evaluation CLI described in <code className="text-slate-300">backend/evals/README.md</code>.
            </EmptyState>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full table-fixed text-left text-sm">
                <thead className="bg-slate-950/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="w-[48%] px-3 py-3 font-medium sm:w-auto sm:px-4">Case</th>
                    <th className="w-[28%] px-2 py-3 font-medium sm:w-36">Agent</th>
                    <th className="w-[24%] px-2 py-3 font-medium sm:w-24">Score</th>
                    <th className="hidden px-4 py-3 font-medium md:table-cell md:w-48">Model</th>
                    <th className="hidden px-4 py-3 font-medium lg:table-cell lg:w-32">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {evals.map((row) => (
                    <tr key={row.id} className="bg-slate-900/40">
                      <td className="break-words px-3 py-3 text-slate-200 sm:px-4">
                        {row.case_id}
                        <span className="mt-1 block break-all text-xs text-slate-600 md:hidden">{row.model}</span>
                      </td>
                      <td className="break-words px-2 py-3 text-slate-300">{humanize(row.agent)}</td>
                      <td className="px-2 py-3 tabular-nums">
                        <span className={clsx(
                          "inline-flex rounded border px-2 py-1 text-xs font-semibold",
                          row.passed
                            ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
                            : "border-red-800 bg-red-950/40 text-red-300",
                        )}>
                          {row.score.toFixed(1)} · {row.passed ? "Pass" : "Fail"}
                        </span>
                      </td>
                      <td className="hidden break-all px-4 py-3 text-xs text-slate-500 md:table-cell">{row.model}</td>
                      <td className="hidden px-4 py-3 text-xs text-slate-500 lg:table-cell">{formatDate(row.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}

function IdeaRows({
  idea,
  expanded,
  verdict,
  onToggle,
  detail,
  loading,
  error,
}: {
  idea: IdeaSummary;
  expanded: boolean;
  verdict: { label: string; className: string };
  onToggle: () => void;
  detail: IdeaDetail | null;
  loading: boolean;
  error: string | null;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className={clsx(
          "min-h-11 cursor-pointer border-t border-slate-800 bg-slate-900/40 transition-colors hover:bg-slate-800/60",
          expanded && "bg-slate-800/60",
        )}
      >
        <td className="break-words px-2 py-1 sm:px-3">
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onToggle();
            }}
            aria-expanded={expanded}
            aria-controls={`idea-detail-${idea.id}`}
            className={clsx(
              "flex min-h-11 w-full flex-col justify-center rounded-md px-1 text-left",
              BUTTON_FOCUS,
            )}
          >
            <span className="font-medium text-slate-200">{idea.title}</span>
            <span className="mt-1 block text-xs text-slate-500 sm:hidden">{formatDate(idea.created_at)}</span>
          </button>
        </td>
        <td className="px-2 py-3 font-mono text-sm tabular-nums text-slate-300">{idea.total_score.toFixed(1)}/10</td>
        <td className="px-2 py-3">
          <span className={clsx("inline-flex rounded border px-2 py-1 text-xs font-medium", verdict.className)}>
            {verdict.label}
          </span>
        </td>
        <td className="hidden px-4 py-3 text-xs text-slate-500 sm:table-cell">{formatDate(idea.created_at)}</td>
      </tr>
      {expanded && (
        <tr className="border-t border-slate-800 bg-slate-950/60">
          <td id={`idea-detail-${idea.id}`} colSpan={4} className="p-3 sm:p-5">
            {loading ? (
              <LoadingState label="Loading idea details…" />
            ) : error ? (
              <div className="rounded-lg border border-red-900/70 bg-red-950/30 p-3 text-sm text-red-200" role="alert">{error}</div>
            ) : detail ? (
              <div className="min-w-0 space-y-5">
                <div>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Description</h3>
                  <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-300">{detail.description}</p>
                </div>

                <div className="overflow-hidden rounded-lg border border-slate-800">
                  <table className="w-full table-fixed text-left text-sm">
                    <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="w-[34%] px-3 py-2 font-medium sm:w-44">Score</th>
                        <th className="px-3 py-2 font-medium">Rationale</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {Object.entries(detail.scores).map(([category, score]) => (
                        <tr key={category}>
                          <td className="break-words px-3 py-3 text-slate-300">
                            {humanize(category)}
                            <span className="ml-2 font-mono tabular-nums text-violet-300">{score.score}/10</span>
                          </td>
                          <td className="break-words px-3 py-3 text-slate-400">{score.rationale}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="grid gap-3 lg:grid-cols-3">
                  <DetailCard title="Best version" body={detail.best_version} tone="emerald" />
                  <DetailCard title="Worst risk" body={detail.worst_risk} tone="red" />
                  <DetailCard title="Validation test" body={detail.validation_test} tone="amber" />
                </div>

                <div>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Next actions</h3>
                  <div className="mt-2 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                    <Markdown>{detail.next_actions}</Markdown>
                  </div>
                </div>
              </div>
            ) : null}
          </td>
        </tr>
      )}
    </>
  );
}

function DetailCard({ title, body, tone }: { title: string; body: string; tone: "emerald" | "red" | "amber" }) {
  const classes = {
    emerald: "border-emerald-900/70 bg-emerald-950/20",
    red: "border-red-900/70 bg-red-950/20",
    amber: "border-amber-900/70 bg-amber-950/20",
  }[tone];
  return (
    <div className={clsx("min-w-0 rounded-lg border p-3", classes)}>
      <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</h3>
      <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-300">{body}</p>
    </div>
  );
}
