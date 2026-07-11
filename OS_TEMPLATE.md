# The Agent Operating System Template

A reusable blueprint for building an AI operating system in **any** domain —
extracted from this repo (a business OS, but nothing below is
business-specific). Follow it to build a legal OS, a health-practice OS, a
content-studio OS, a research OS. The architecture survived two builds: the
operations layer (Phases 1-4) and the venture layer (Phases V1-V5), the
second implemented largely by a *different model* working from these
patterns — which is the point: **intelligence lives in the structure, not
the model**.

---

## 1. The core thesis

An agent OS is not a chatbot with tools. It is:

> **Prompt-driven agents that think + deterministic code that sequences,
> validates, and persists + structure that survives model downgrades.**

Every decision below follows from three rules:

1. **Agents never write to systems of record.** They *propose* through
   validated tools; deterministic code checks every field and performs the
   write. One write path per table, ever.
2. **Anything that can be deterministic must be.** Routing rules, scoring
   thresholds, workflow sequencing, report assembly, evaluation rubrics —
   all code, not model judgment. The model supplies analysis; code supplies
   arithmetic, order, and verdicts.
3. **Quality must be measurable and portable.** Structural evals prove
   whether a cheaper model is good enough; survival guides transfer the
   strong model's discipline to weaker ones.

## 2. The layer stack (build in this order)

```
7. UI            one page per surface; poll, don't stream, until you need streaming
6. Evals         scenario cases + deterministic rubric + runner  ← proves layer 3-5 quality
5. Workflows     deterministic orchestration of multiple agents (debate, simulate, generate)
4. Memory        curated records with categories, access matrix, validated writes
3. Agents        one Agent class, many configs (prompt + least-privilege tool subset)
2. Tools         SELECT-only reads; validated write tools; sandboxed compute
1. Data          one schema, seedable with synthetic data, reconcilable by design
0. Guardrails    budgets, depth limits, human approval gates, JSONL audit logs
```

## 3. What to build per layer (the checklist)

### Layer 0 — Guardrails (before any agent exists)
- [ ] Token budget shared across a whole request tree; hard stop when spent.
- [ ] Delegation depth limit (2 is plenty).
- [ ] JSONL decision log: every run, every tool call, inputs and outputs.
- [ ] Human approval inbox: anything outward-facing lands as *pending*;
      nothing external happens without a click.
- [ ] A demo mode (see §5) so the whole system runs at $0.

### Layer 1 — Data
- [ ] One ORM schema; every table documents its conventions in the docstring.
- [ ] A synthetic data generator whose numbers *reconcile* (an auditor agent
      must be able to check sums across tables) — this is what makes agent
      answers verifiable.
- [ ] A provider interface so synthetic data can be swapped for real data
      without agents noticing.

### Layer 2 — Tools
- [ ] `sql_query`: SELECT-only, enforced at the engine level (read-only
      connection + authorizer), per-agent table allowlists, row caps.
- [ ] Sandboxed compute (`python_calc`): import allowlist, subprocess
      isolation, timeouts — agents must not do arithmetic "in their head".
- [ ] Validated write tools, one per record type, all shaped like:
      `make_X_tool(engine)` factory → handler validates every field
      (raising a ToolError the model can read) → single deterministic write
      function → human-readable confirmation string.

### Layer 3 — Agents
- [ ] One `Agent` class; an agent = name + system prompt + tool-name subset
      + model + caps. No subclasses.
- [ ] Least privilege everywhere: each agent sees only its tables' schema
      docs and only its tools.
- [ ] An orchestrator whose ONLY tools are `get_roster` and `delegate` — it
      routes and synthesizes with attribution, never answers from memory.
- [ ] Parallel fan-out: all tool calls in one model turn run concurrently.
- [ ] Prompts state: role, method (numbered), conventions, and a **required
      output structure**. A unique marker phrase per prompt (demo mode and
      survival injection key on it).
- [ ] Domain skeptics, not just doers: your equivalent of red team / risk
      officer / per-domain critics. Every OS needs agents whose job is
      attacking plans.

### Layer 4 — Memory
- [ ] A `memories` table: category (fixed list), title, content, source,
      soft link to the subject, active/archived, timestamps.
- [ ] A design doc per category: when to save / retrieve / update / delete,
      example record, agent access matrix.
- [ ] Writes only via a validated `save_memory` tool with a **per-agent
      category allowlist**, plus automatic saves from workflow code
      (decisions, research, risks — code decides, not agent discretion).
- [ ] A profile of the *principal human* (the "founder clone" pattern): the
      16-ish fields that make every recommendation specific to them,
      prepended to workflow briefs by code.

### Layer 5 — Workflows
- [ ] Deterministic orchestration functions, never chat delegation:
      `run_X(service, engine, topic) -> report_id`, one budget per workflow,
      every brief starts with a parseable `TOPIC:` line and gets the
      profile + memory context appended by code.
- [ ] The four archetypes (rename per domain):
      **Debate** (propose → parallel domain attacks → evidence check →
      revision + decision with owner/deadline/reversal trigger),
      **Failure simulation** (adversaries project failure over time
      horizons), **Synthetic panel** (simulated stakeholder interviews,
      loudly labeled synthetic), **Strict scoring** (model proposes
      per-category scores; code computes the verdict from fixed thresholds
      the model cannot override).
- [ ] Agent failures become report content (`[X unavailable: …]`), never
      workflow crashes.
- [ ] Every workflow persists a report (its narrative) and a memory record
      (its retrievable conclusion).
- [ ] A deterministic router: keyword rule table mapping request types →
      primary/supporting agents, workflow sequence, risk level, required
      inputs — with domain modifiers that only *escalate* risk, and
      warnings sourced from memory (e.g. "a similar idea was already
      rejected").

### Layer 6 — Evals
- [ ] Scenario cases as data (JSON): input scenario, expected elements
      (weighted regex), bad signs (penalties), numeric-anchor minimum,
      pass threshold, improvement suggestions. ≥2 per agent role.
- [ ] A deterministic rubric: matched-weight share → 0-10, minus penalties;
      same text always scores the same. No model judges another model by
      default (an LLM judge is an optional add-on).
- [ ] A runner with a library function (tests) and a CLI (humans) that runs
      cases through the *real* runtime, persists results, prints a
      per-agent scoreboard.
- [ ] The model-comparison loop: baseline on the strong model → candidate
      on the cheap model → candidate + survival mode → compare averages.
- [ ] Meta-tests: every case file validates; a case's own improvement
      suggestions must NOT pass its rubric (guards against trivial regexes).

### Layer 7 — UI
- [ ] One page per surface: overview (KPIs), chat (live delegation tree),
      activity (runs + cost), documents, approvals, and the domain studio
      (run workflows, browse scored subjects, router tester, profile
      editor, memory browser, playbook library).
- [ ] Trigger-then-poll beats streaming for workflows; streaming is only
      worth it for chat.
- [ ] Badge metadata per document kind; unknown kinds must render gracefully.

## 4. The Model Downgrade Survival Kit (do this early, not last)

For every agent, a guide file with: role definition, thinking framework,
decision principles, required output structure, excellent vs. poor answer
examples, common mistakes, self-review checklist, quality checklist — plus a
machine-readable block (`<!-- SURVIVAL:PROMPT:START/END -->`) that a
`SURVIVAL_MODE` flag appends to the system prompt at construction. Weak
models keep the strong model's discipline because the discipline is written
down. Measure the effect with the eval runner; don't assume it.

## 5. Demo mode (the pattern nobody regrets)

A drop-in fake model client that: identifies the agent by a unique marker
substring in its system prompt, runs canned rule-based "reasoning" per agent,
but executes every TOOL for real (live SQL, real validated writes). The
whole OS — including multi-agent workflows — runs end-to-end at $0. This is
your test fixture, your sales demo, and your CI safety net in one. Add a
marker + handler for every new agent, and a regression test asserting every
agent's prompt resolves to exactly its own handler.

## 6. Multi-agent development protocol (how this repo was actually built)

Two AI agents, one architect (strong model) + one implementer, GitHub as the
only source of truth:

- `AGENTS.md` in repo root: hard rules, architecture map, gotchas, commands,
  branch ownership (architect owns the integration branch; implementer owns
  `impl/<task-id>` branches; nobody touches the other's branches).
- Task packets (`docs/tasks/`): TASK ID, BASE SHA, objective, in/out of
  scope files, functional requirements (may delegate to a full spec),
  acceptance criteria, required tests, security/edge cases, known risks.
- Review loop: implementer pushes → architect reviews the exact diff +
  reruns all gates + returns findings as
  BLOCKING / IMPORTANT / OPTIONAL + verdicts + ACCEPT/REQUEST CHANGES,
  committed to `docs/tasks/<id>-REVIEW.md` → merge only when no BLOCKING.
- Per-phase reviews are blocking-only; a full audit-and-fix pass by the
  architect closes the project.
- Ambiguity rule: choose the interpretation touching the least existing
  code; record the decision in the commit body.

## 7. Porting guide — from this repo to a new domain

| This repo (business OS) | Your new OS |
|---|---|
| Lumina Labs synthetic dataset | Your domain's records (cases, patients, projects…) with reconcilable numbers |
| CEO / CFO / CMO / CTO / Researcher | Orchestrator + your 3-6 domain specialists |
| Venture critics (CFO/CMO/CTO/COO/Risk skeptics) | Your domain's adversarial reviewers |
| Debate workflow (board meeting) | Any major-decision review ritual |
| Failure simulator | Pre-mortem for your domain's plans |
| Synthetic customer interviews | Synthetic stakeholder/user/patient panel |
| Idea scoring engine (14 categories, strict thresholds) | Your triage/scoring rubric — keep the "model proposes, code decides" split |
| Founder clone | The principal's profile (client, patient, editor…) |
| 16 memory categories | Your domain's memory taxonomy |
| Playbook library | Your domain's reusable procedures |
| Approvals inbox for marketing content | Human gate on anything leaving the system |
| Eval cases per agent role | Same, with your domain's quality bars |

**Porting order:** copy the skeleton (layers 0-2 are domain-neutral) →
rename agents + rewrite prompts/output structures → rewrite the scoring
categories, router rules, and memory taxonomy (docs first, then the mirrors
in code) → regenerate survival guides → write eval cases → keep demo mode
alive from day one.

## 8. Definition of done (per phase and overall)

A phase is done when: everything runs, the full test suite is green, demo
mode covers the new surface, and the docs that mirror code (router rules,
memory categories, scoring thresholds) match it. The OS is done when a new
user can: ask the orchestrator a question and verify the answer against the
data; run every workflow at $0; see every decision logged; find every
verdict computed by code they can read; and run the evals against a cheaper
model to decide what it may safely operate.
