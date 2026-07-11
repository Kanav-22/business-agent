# Task V3 — Venture workflows (debate, failure sim, interviews, idea score)

**Branch:** `codex/v3-workflows` (from latest `claude/agent-operating-system-66e55h`)
**Read first:** `AGENTS.md`, `backend/app/scheduler.py` (the pattern to copy),
`backend/app/venture/agents.py`, `backend/app/agents/simulated.py` (venture
handlers), `backend/app/api/venture.py`, `docs/MEMORY_SYSTEM.md`.

## Goal

Four parameterized multi-agent workflows that run the venture agents directly
(scheduler-job pattern), save a markdown report + memory record, and are
triggerable via REST. All four must work end-to-end at $0 with `DEMO_MODE=1`.

## 1. `backend/app/venture/workflows.py`

Module docstring: workflows are deterministic orchestration code — agents
think, code sequences/validates/persists.

Shared helpers (private):

```python
async def _noop_event(event: dict) -> None: ...

def _brief(topic: str, instructions: str, engine) -> str:
    # ALWAYS starts with f"TOPIC: {topic}\n" (demo handlers parse this line),
    # then instructions, then founder_context(engine) and
    # memory_context(engine, limit=8) blocks when non-empty, separated by
    # blank lines.

async def _run(service, agent_name: str, task: str, budget, on_event) -> str:
    # venture_team lookup ∪ {"researcher": service.specialists["researcher"]};
    # returns result.output, or f"[{display_name} unavailable: {error}]" on
    # result.error — workflows must NEVER raise because one agent failed.
```

Every public workflow: signature
`async def run_X(service, engine, topic: str, *, on_event=None) -> int`
(returns the saved report id), creates ONE
`TokenBudget(limit=service.settings.token_budget)` for the whole workflow,
uses `on_event or _noop_event`, and saves via
`save_report(engine, title=..., content=..., agent=..., kind=...)`.

### `run_debate` — kind `debate`, agent `venture_ceo`

The board meeting. Sequence:

1. `venture_ceo` — brief: "Propose a strategy for this topic…" → proposal.
2. **In parallel** (`asyncio.gather`), each with the proposal embedded in the
   brief: `venture_cfo` (financial attack), `venture_cmo` (demand attack),
   `venture_cto` (feasibility attack), `coo` (execution attack), `risk`
   (legal/reputational attack).
3. `researcher` — assumption check brief listing the proposal's numbered
   assumptions. (Demo mode returns its "needs an API key" text — include it
   verbatim; that is acceptable.)
4. `venture_ceo` — revision brief containing ALL objections; the brief text
   MUST contain the words "Revise" and "objections" (demo handler triggers on
   both, lowercase check).

Report title: `Board debate: {topic}` (truncate topic at 150 chars). Sections,
exactly these headings in this order:

```
## Original proposal
## Agent objections        (subsections: ### CFO … ### CMO … ### CTO … ### COO … ### Risk Officer)
## Researcher — assumption check
## Counterarguments & revision   (the venture_ceo revision output — it contains
                                  Revised plan / Final decision / Remaining risks /
                                  Execution steps / Owner / Deadline)
```

After saving the report, save a memory (deterministic code, NOT an agent):
`save_memory_record(engine, category="decision", title=f"Debate decision: {topic}"[:200],
content=<first 1500 chars of the revision output> + f" Full report: #{report_id}.",
source_agent="venture_ceo", related_idea=topic[:80])`.

### `run_failure_simulation` — kind `failure_sim`, agent `red_team`

In parallel: `red_team` and `risk`. Brief instructs simulating failure over
**7 days, 30 days, 90 days, 1 year**, and for each failure mode: failure mode,
cause, early warning signs, probability (L/M/H), damage level, prevention
plan, recovery plan, agent responsible. Report title
`Failure simulation: {topic}`; sections `## Red team — failure modes`,
`## Risk officer — exposure`, plus a fixed closing section
`## How to use this` (2-3 sentences: prevention plans become tasks, early-warning
signs become weekly checks). Memory: category `risk`, title
`Failure modes: {topic}`, content = first 1500 chars of red_team output +
report ref, source_agent `red_team`.

### `run_customer_interviews` — kind `interviews`, agent `interviewer`

Single `interviewer` call. Brief: generate 20 personas with all 13 fields +
the synthesis (see the agent's prompt). Report title
`Synthetic interviews: {topic}`. The report MUST begin with a bold disclaimer
line that these are synthetic interviews requiring real validation (add it in
code; don't rely on the model). Memory: category `customer_research`, title
`Synthetic interviews: {topic}`, content = the synthesis portion if findable
(text from "Synthesis" onward) else first 1500 chars, source_agent
`interviewer`.

### `run_idea_score` — kind `idea_score`, agent `scorer`

Single `scorer` call (its `score_idea` tool already persists the Idea row +
memory). After the run, fetch the newest idea via `list_ideas(engine, limit=1)`
→ `get_idea`. If no idea was created (model failed to call the tool), still
save a report saying so and return its id. Otherwise compose the report from
the idea record: total score + verdict (use `VERDICT_LABELS`), scoreboard
table via `render_scoreboard` (scores/rationales come from
`idea["scores"]` → `{k: v["score"]}` / `{k: v["rationale"]}`), best version,
worst risk, cheapest validation test, next actions, and the scorer's closing
text. Title: `Idea score: {idea title}`.

### Registry

```python
VENTURE_WORKFLOWS: dict[str, dict] = {
  "debate":      {"run": run_debate, "label": "Board debate",
                  "description": "CEO proposes; CFO/CMO/CTO/COO/Risk attack; researcher checks; CEO decides."},
  "failure_sim": {"run": run_failure_simulation, ...},
  "interviews":  {"run": run_customer_interviews, ...},
  "idea_score":  {"run": run_idea_score, ...},
}
```

## 2. `backend/app/main.py` (additive)

In the venture-layer section:

- `GET /api/venture/workflows` → `[{name, label, description}]`.
- `POST /api/venture/{workflow_name}` body `{"topic": str}` (new
  `WorkflowBody` pydantic model) → 404 unknown name, 400 empty topic
  (strip; also cap at 500 chars with 400 above), 409 if `f"venture:{name}"`
  already in the existing `jobs_in_flight` set, else 202
  `{"started": true, "workflow": name}` and run in a background task exactly
  like `run_job` does (try/except log, discard in `finally`).

## 3. Tests — `backend/tests/test_venture_workflows.py`

Use `FakeClient` dict mode keyed by these marker substrings:
`"venture strategist"` (queue TWO responses: proposal text, then revision
text), `"financial skeptic"`, `"demand skeptic"`, `"feasibility skeptic"`,
`"COO agent"`, `"Risk Officer agent"`, `"Researcher agent"`,
`"Red Team agent"`, `"Interviewer agent"`, `"Idea Scorer agent"` (queue a
`tool_use_block` calling `score_idea` with valid input — copy a valid payload
shape from `tests/test_scoring.py::tool_input` — then a text response).
Copy the seeded DB (`writable_settings` pattern from `test_phase4.py`).

Must cover at least:
1. `run_debate`: returns a report id; report kind `debate` contains all four
   `##` headings and the CFO objection text; a `decision` memory row exists
   referencing the report id; the two venture_ceo calls happened (queue
   exhaustion proves it).
2. `run_failure_simulation`: report saved with both agent sections; `risk`
   memory row exists.
3. `run_customer_interviews`: report begins with the synthetic disclaimer;
   `customer_research` memory exists.
4. `run_idea_score`: Idea row created (via the real tool), report contains the
   verdict label and the scoreboard table header.
5. One agent erroring (script an exception or exhaust its queue → the fake
   raises `AssertionError`; easier: script `venture_cfo` with zero responses
   is NOT allowed — instead monkeypatch one agent's `run` to return an
   `AgentResult` with `error="model_error"`) → workflow still saves a report
   containing `unavailable`.
6. API: unknown workflow 404; empty topic 400; happy path 202 (script demo:
   easiest is `DEMO_MODE` settings → `AgentService(settings)` with
   `demo_mode=True` and no client factory override, then poll
   `list_reports(kind=...)` briefly, or call the workflow function directly
   and only assert the endpoint's 202/404/400 contract with a monkeypatched
   registry entry).

## Acceptance checklist

- [ ] `python3 -m pytest` green (85 existing + new).
- [ ] `DEMO_MODE=1` manual smoke: POST each of the four workflows with topic
      "Launch an AI tool for doctors" → four reports appear under
      `/api/reports?kind=...`, one idea in `/api/ideas`, memories in
      `/api/memories` (categories decision/risk/customer_research/business_idea).
- [ ] No changes outside: `backend/app/venture/workflows.py`,
      `backend/app/main.py` (venture section + one pydantic model),
      `backend/tests/test_venture_workflows.py`.
