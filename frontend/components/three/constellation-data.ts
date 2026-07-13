export type ConstellationNode = {
  readonly key: string;
  readonly label: string;
  readonly color: string;
  readonly position: readonly [number, number, number];
  readonly phase: number;
};

export const CEO_NODE = {
  key: "ceo",
  label: "CEO",
  color: "#a78bfa",
  position: [0, 0, 0] as const,
};

// These colors mirror the operating roster in backend/app/agents/service.py.
// The nine orbiting nodes are the five CEO specialists plus the CFO's four
// finance specialists, which keeps the hero faithful to the real delegation
// graph without making the scene visually dense.
export const AGENT_NODES: readonly ConstellationNode[] = [
  {
    key: "coordinator",
    label: "Coordinator",
    color: "#94a3b8",
    position: [0, 2.75, -0.4],
    phase: 0.2,
  },
  {
    key: "cmo",
    label: "CMO",
    color: "#f472b6",
    position: [1.95, 2.05, 0.25],
    phase: 1.1,
  },
  {
    key: "researcher",
    label: "Researcher",
    color: "#fbbf24",
    position: [3.05, 0.6, -0.45],
    phase: 2.15,
  },
  {
    key: "cto",
    label: "CTO",
    color: "#38bdf8",
    position: [2.65, -1.25, 0.5],
    phase: 3.05,
  },
  {
    key: "control",
    label: "Control",
    color: "#fb7185",
    position: [1.0, -2.6, -0.2],
    phase: 3.8,
  },
  {
    key: "revenue",
    label: "Revenue",
    color: "#4ade80",
    position: [-1.1, -2.55, 0.35],
    phase: 4.7,
  },
  {
    key: "cfo",
    label: "CFO",
    color: "#34d399",
    position: [-2.65, -1.2, -0.5],
    phase: 5.55,
  },
  {
    key: "fpa",
    label: "FP&A",
    color: "#2dd4bf",
    position: [-3.0, 0.65, 0.4],
    phase: 6.35,
  },
  {
    key: "reporting",
    label: "Reporting",
    color: "#a3e635",
    position: [-1.85, 2.0, 0.3],
    phase: 7.2,
  },
];
