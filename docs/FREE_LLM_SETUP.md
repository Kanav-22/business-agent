# Running the OS on a Free LLM

How to point the whole system at a free (non-Anthropic, non-OpenAI-billed)
model, which model to pick, and how to keep quality acceptable. Written for
the scenario this OS was designed to survive: the strong model that built it
is gone.

## What the backend actually requires

The agent loop speaks the **Anthropic Messages API** (`client.messages.create`
with `system`, `tools`, `messages`, tool_use/tool_result blocks). So any
model works if two things are true:

1. Something exposes it behind an **Anthropic-compatible endpoint**.
2. The model has **reliable function/tool calling** — every agent works
   through tools; a model that fumbles tool JSON is unusable here no matter
   how well it writes.

There is no OpenAI SDK path in this codebase, on purpose: one client shape,
one proxy layer, swap anything behind it.

## Setup (recommended path: LiteLLM proxy)

LiteLLM is a free, self-hosted proxy that translates the Anthropic Messages
format to ~100 providers, including all the free-tier ones.

```bash
pip install "litellm[proxy]"
```

`litellm_config.yaml`:

```yaml
model_list:
  - model_name: business-os          # what AGENT_MODEL will reference
    litellm_params:
      model: gemini/gemini-2.5-flash # or groq/llama-3.3-70b-versatile, ollama/qwen3:32b …
      api_key: os.environ/GEMINI_API_KEY
```

```bash
export GEMINI_API_KEY=...            # free key from Google AI Studio
litellm --config litellm_config.yaml --port 4000
```

Then run the backend against the proxy:

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000   # the anthropic SDK honors this
export ANTHROPIC_API_KEY=anything-nonempty        # LiteLLM master key if you set one
export AGENT_MODEL=business-os
export WEB_TOOLS_ENABLED=0                        # REQUIRED off-Anthropic (see below)
export SURVIVAL_MODE=1                            # REQUIRED for weaker models (see below)
python3 -m uvicorn app.main:app --port 8000
```

Verify the proxy speaks the right dialect before blaming the app:
`curl http://localhost:4000/v1/messages -H "content-type: application/json" -d '{"model":"business-os","max_tokens":50,"messages":[{"role":"user","content":"say ok"}]}'`
(LiteLLM added the Anthropic-format `/v1/messages` endpoint; if your
installed version lacks it, upgrade LiteLLM — check their current docs, this
moves fast.)

### Why `WEB_TOOLS_ENABLED=0` is required

`web_search`/`web_fetch` are Anthropic **server-side** tools — executed
inside Anthropic's API, not locally. Any other backend rejects those
declarations. The flag strips them from the Researcher, CMO, and Content
configs. Consequence: the Researcher can no longer browse — it degrades to
reasoning without citations, and researcher eval cases will rightly score
low. Everything else (SQL, calc, all validated writes, all four venture
workflows, evals) is local and unaffected.

## Which free model (candid guidance, verify current free tiers)

Free quotas and model names change monthly; my knowledge has a cutoff.
Treat this as a starting shortlist, then let the eval runner decide.

| Candidate | Why | Watch out |
|---|---|---|
| **Gemini 2.5 Flash (Google AI Studio free tier)** — first pick | Strong tool calling, long context, generous free quota, fast | Daily rate limits; data-use terms on the free tier |
| **Groq free tier (Llama 3.3 70B class)** | Very fast, decent tool use | Tighter rate limits; occasionally sloppy tool JSON |
| **DeepSeek chat** | Near-free pricing, strong reasoning | Not strictly free; API stability varies |
| **OpenRouter `:free` pool** | Rotating free models behind one API | Availability/quality vary week to week |
| **Local via Ollama (Qwen-class 14-32B)** | Truly free, private | Tool calling is the weak spot below ~30B; needs real hardware |

## How to choose: measure, don't guess

This is exactly what the V4 eval system is for. For each candidate:

```bash
cd backend
AGENT_MODEL=<candidate> WEB_TOOLS_ENABLED=0                 python3 -m evals.runner --save-report
AGENT_MODEL=<candidate> WEB_TOOLS_ENABLED=0 SURVIVAL_MODE=1 python3 -m evals.runner --save-report
```

Compare per-agent averages across runs (`/api/evals` or the saved eval
reports). Selection rules of thumb:

- Ignore the `researcher` rows (no web tools) — judge the other 8 roles.
- A model is *acceptable* for a role at average ≥ 6; *good* at ≥ 7.5.
- The survival-mode run should beat the plain run; if it doesn't, the model
  is ignoring instructions — disqualify it.
- If only some roles pass, you can still use the model: keep the failing
  roles' work manual until you upgrade.

Also run the free operational check: `DEMO_MODE=1` needs no model at all —
keep using it for anything that's really tool work, and spend model calls
only where reasoning matters.

## Keeping an inferior model at standard

Three layers already in the product do this — turn them all on:

1. **`SURVIVAL_MODE=1`** injects (a) the *global weak-model operating
   protocol* — thinking order, analysis order, output discipline, forbidden
   moves (`docs/survival/GLOBAL_PROTOCOL.md`) — into every agent, and (b)
   the per-role guide scaffolding (`docs/survival/*.md`) on top.
2. **Deterministic spine**: verdicts, routing, workflow order, report
   assembly, and eval scores are computed by code — the model cannot ruin
   them, only the prose around them.
3. **Evals as the gate**: never promote a model to a role it hasn't passed.

Budget guards for small free quotas: lower `AGENT_TOKEN_BUDGET` (e.g.
60000) and expect slower, retry-prone runs at peak times — the workflows
tolerate individual agent failures by design (`[X unavailable: …]`).
