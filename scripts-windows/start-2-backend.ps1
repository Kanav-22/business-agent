# Window 2 of 3 — the Business OS backend, running on Gemini via the proxy.
# Start scripts-windows/start-1-proxy.ps1 in another window FIRST.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "backend")

# --- one-time setup (safe to re-run; fast when already done) ------------------
if (-not (Test-Path ".venv")) {
    Write-Host "First run: creating the Python environment (one-time)..." -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    else { & python -m venv .venv }
}
& .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
& .venv\Scripts\python.exe scripts\seed.py

# --- point the app at the proxy (your key stays in gemini-key.txt) ------------
$env:ANTHROPIC_BASE_URL = "http://localhost:4000"
$env:ANTHROPIC_API_KEY  = "proxy-holds-the-real-key"
$env:AGENT_MODEL        = "business-os"
$env:WEB_TOOLS_ENABLED  = "0"   # Gemini can't run Anthropic's server-side web tools
$env:SURVIVAL_MODE      = "1"   # weak-model scaffolding on

Write-Host ""
Write-Host "Backend starting on http://localhost:8000 — keep this window open." -ForegroundColor Green
& .venv\Scripts\uvicorn.exe app.main:app --port 8000
