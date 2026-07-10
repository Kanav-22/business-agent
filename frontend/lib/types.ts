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
