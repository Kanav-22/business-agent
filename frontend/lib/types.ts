export interface Kpis {
  company: string;
  window_start: string;
  window_end: string;
  mrr: number;
  active_customers: number;
  cash: number;
  avg_monthly_burn: number;
  runway_months: number | null;
  open_tasks: number;
  last_month: string | null;
  last_month_revenue: number;
  last_month_expenses: number;
  last_month_profit: number;
  revenue_mom_pct: number | null;
}

export interface MonthPoint {
  month: string;
  revenue: number;
  expenses: number;
  profit: number;
}

/** One row of the Agent Activity feed (from /api/activity). */
export interface ActivityRun {
  run_id: string;
  parent_run_id: string | null;
  agent: string;
  agent_display: string;
  color: string;
  depth: number;
  task: string;
  started_at: number;
  status: "running" | "completed" | "error";
  error: string | null;
  duration_ms: number | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  tools: { tool: string; count: number }[];
}

export interface ReportSummary {
  id: number;
  title: string;
  kind:
    | "report"
    | "briefing"
    | "control_check"
    | "research"
    | "content"
    | "debate"
    | "failure_sim"
    | "interviews"
    | "idea_score"
    | "intake"
    | "eval";
  agent: string;
  created_at: string;
  excerpt: string;
}

export interface VentureWorkflow {
  name: string;
  label: string;
  description: string;
}

export type IntakeQuestionType = "short" | "long" | "number" | "choice";

export interface IntakeQuestion {
  key: string;
  section: string;
  question: string;
  type: IntakeQuestionType;
  choices?: string[];
  required: boolean;
  why: string;
}

export interface IntakeUpload {
  key: string;
  label: string;
  accepts: string;
  purpose: string;
}

export interface IntakeQuestionsResponse {
  sections: string[];
  questions: IntakeQuestion[];
  uploads: IntakeUpload[];
}

export type BusinessProfile = Record<string, string>;

export interface IntakeUploadResponse {
  stored: boolean;
  next?: string;
}

export interface IdeaSummary {
  id: number;
  title: string;
  total_score: number;
  verdict: "go" | "no_go" | "test_first";
  created_at: string;
  excerpt: string;
}

export interface IdeaDetail extends Omit<IdeaSummary, "excerpt"> {
  description: string;
  scores: Record<string, { score: number; rationale: string }>;
  best_version: string;
  worst_risk: string;
  validation_test: string;
  next_actions: string;
}

export interface RouteDecision {
  category: string;
  primary_agent: string;
  supporting_agents: string[];
  workflow: string[];
  risk_level: "low" | "medium" | "high";
  reason: string;
  required_inputs: string[];
  expected_output: string;
  matched_categories: string[];
  founder_fit_note: string | null;
  warnings: string[];
}

export type FounderProfileKey =
  | "skills"
  | "weaknesses"
  | "working_style"
  | "risk_tolerance"
  | "budget_range"
  | "long_term_goals"
  | "current_assets"
  | "coding_ability"
  | "business_interests"
  | "communication_style"
  | "decision_flaws"
  | "how_to_challenge"
  | "how_to_focus"
  | "distracting_ideas"
  | "avoid"
  | "double_down";

export type FounderProfile = Record<FounderProfileKey, string>;

export interface Memory {
  id: number;
  category: string;
  title: string;
  content: string;
  source_agent: string;
  related_idea: string | null;
  status: "active" | "archived";
  created_at: string;
}

export interface PlaybookSummary {
  slug: string;
  title: string;
}

export interface Playbook {
  slug: string;
  content: string;
}

export interface EvalRow {
  id: number;
  case_id: string;
  agent: string;
  model: string;
  score: number;
  passed: boolean;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Approval {
  id: number;
  kind: string;
  title: string;
  channel: string;
  agent: string;
  status: "pending" | "approved" | "rejected";
  content: string;
  created_at: string;
  decided_at: string | null;
  note: string | null;
  published_report_id?: number;
}

export interface ReportDetail extends Omit<ReportSummary, "excerpt"> {
  content: string;
}

/** Events streamed over /ws/chat while the delegation tree runs. */
export interface AgentEvent {
  type:
    | "run_started"
    | "agent_text"
    | "tool_call"
    | "tool_result"
    | "run_completed"
    | "done"
    | "error";
  ts?: number;
  run_id?: string;
  parent_run_id?: string | null;
  agent?: string;
  agent_display?: string;
  color?: string;
  depth?: number;
  // run_started
  task?: string;
  // agent_text
  text?: string;
  // tool_call / tool_result
  tool?: string;
  tool_use_id?: string;
  input?: Record<string, unknown>;
  output?: string;
  is_error?: boolean;
  // run_completed / done
  error?: string | null;
  duration_ms?: number;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total?: number;
    limit?: number;
  };
  // error
  message?: string;
}
