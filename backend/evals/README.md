# Agent evaluations

The evaluation harness sends realistic founder scenarios through the same agent
objects used by the application, scores each response with a deterministic
structural rubric, stores the result in `eval_results`, and prints role and overall
averages. It is a comparison instrument, not an LLM judge: identical text receives
an identical score every time.

Run commands from `backend/`:

```bash
# Zero-cost smoke using the simulated client
DEMO_MODE=1 python3 -m evals.runner --save-report

# Current configured baseline
python3 -m evals.runner --save-report

# Candidate model, then the same candidate with survival scaffolding
AGENT_MODEL=<candidate> python3 -m evals.runner --save-report
AGENT_MODEL=<candidate> SURVIVAL_MODE=1 python3 -m evals.runner --save-report

# Discovery and focused runs
python3 -m evals.runner --list
python3 -m evals.runner --agent risk
python3 -m evals.runner --case risk_patient_data_compliance
```

The console scoreboard and optional `kind="eval"` report show each case, per-agent
averages, and the overall average. Persisted rows are also available from
`GET /api/evals`; filter that endpoint by `agent` when comparing one role.

## How scoring works

Every case assigns weights to required structural elements. The rubric converts the
matched-weight share to a score out of 10, subtracts case-specific and universal bad
signs, subtracts 1.5 when too few numeric anchors appear, clamps the result to 0-10,
and compares it with the case's `pass_score`. Failed cases retain their authored
improvement suggestions in the persisted details.

## Add a case

Add one UTF-8 JSON file under `evals/cases/` with a unique ID, supported agent role,
`TOPIC:`-first scenario, weighted regex expectations, bad signs, numeric minimum,
pass score, and practical suggestions. `python3 -m evals.runner --list` validates all
files and reports the filename when a schema or regex is invalid. Keep patterns
structural and specific; the case's own suggestions should score below its pass bar.

## Compare models

1. Run and save the configured baseline.
2. Run the candidate with survival mode off.
3. Run the same candidate with `SURVIVAL_MODE=1`.
4. Compare per-agent averages across the three printed tables, saved reports, or
   `/api/evals` rows. The survival kit is helping when step 3 recovers a meaningful
   share of the baseline-to-candidate gap without introducing new bad signs.
