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
  kind: "report" | "briefing" | "control_check" | "research" | "content";
  agent: string;
  created_at: string;
  excerpt: string;
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
