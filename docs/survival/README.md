# Model Downgrade Survival Kit

These guides preserve agent intelligence **through structure** when the underlying
model gets weaker. A powerful model behaves well with a short prompt; a weaker model
needs the thinking framework, output structure, and self-review checklist spelled out.

## How the kit works

Each guide has two audiences:

1. **Humans** — the full guide: role definition, thinking framework, decision
   principles, required output structure, excellent vs. poor answer examples, common
   mistakes, self-review checklist, final quality checklist.
2. **The runtime** — a compact block between `<!-- SURVIVAL:PROMPT:START -->` and
   `<!-- SURVIVAL:PROMPT:END -->`. When the backend runs with `SURVIVAL_MODE=1`,
   `backend/app/agents/survival.py` extracts that block and appends it to the matching
   agent's system prompt at construction time. Default is **off** — the current
   product behaves exactly as before.

```bash
export SURVIVAL_MODE=1        # inject survival scaffolding into system prompts
export AGENT_MODEL=claude-haiku-4-5-20251001   # e.g. when downgrading models
```

## Guide → agent mapping

| Guide | Runtime agent |
|-------|---------------|
| `CEO_AGENT_SURVIVAL_GUIDE.md` | `ceo` |
| `CFO_AGENT_SURVIVAL_GUIDE.md` | `cfo` |
| `CMO_AGENT_SURVIVAL_GUIDE.md` | `cmo` |
| `CTO_AGENT_SURVIVAL_GUIDE.md` | `cto` |
| `COO_AGENT_SURVIVAL_GUIDE.md` | `coo` (venture layer) |
| `RESEARCH_AGENT_SURVIVAL_GUIDE.md` | `researcher` |
| `SALES_AGENT_SURVIVAL_GUIDE.md` | `sales` (venture layer) |
| `RISK_AGENT_SURVIVAL_GUIDE.md` | `risk` (venture layer) |
| `BOARD_AGENT_SURVIVAL_GUIDE.md` | the debate workflow (doc-only; the CEO applies it when synthesizing a debate) |

## Measuring whether the kit works

Run the evaluation system (`backend/evals/`) against the strong model, record scores,
then switch `AGENT_MODEL` to the weaker model and run again — once with
`SURVIVAL_MODE=0` and once with `SURVIVAL_MODE=1`. The kit is working when the
survival-mode scores recover most of the gap.
