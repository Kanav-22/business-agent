# Task V10 — CI pipeline (GitHub Actions)

**Branch:** `codex/v10-ci` (from latest `claude/agent-operating-system-66e55h`)
**Read first:** `AGENTS.md` (gates), `backend/requirements.txt`,
`frontend/package.json`.

## Goal

Every push to any branch runs the same gates the review protocol runs by
hand: full backend pytest and the frontend production build. No secrets
required — tests use the scripted fake client and demo modes.

## 1. `.github/workflows/ci.yml`

Triggers: `push` (all branches) and `pull_request`. Two independent jobs:

- **backend**: ubuntu-latest, Python 3.11 (`actions/setup-python` with pip
  cache keyed on `backend/requirements.txt`), `pip install -r
  backend/requirements.txt`, `python -m pytest -q` with working-directory
  `backend`. No ANTHROPIC_API_KEY anywhere.
- **frontend**: ubuntu-latest, Node 20 (`actions/setup-node`, npm cache
  keyed on `frontend/package-lock.json`), `npm ci` + `npm run build` with
  working-directory `frontend`. Set `NEXT_TELEMETRY_DISABLED: 1`.

Keep it minimal: no matrix, no lint step (none configured in the repo), no
artifact uploads, timeout-minutes 15 per job.

## 2. README (append-only)

Add the workflow status badge line directly under the H1.

## Acceptance checklist

- [ ] YAML parses (`python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`
      — pyyaml is available transitively; if not, any equivalent local check).
- [ ] Both jobs' commands run green LOCALLY exactly as written in the YAML
      (same working directories) — state this in the commit body.
- [ ] Files touched: `.github/workflows/ci.yml` (new) + one README badge
      line. Nothing else.
- [ ] The pushed branch's own Actions run is green (the architect verifies
      via the GitHub API during review).
