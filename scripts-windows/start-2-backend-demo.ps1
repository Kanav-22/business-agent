# Alternative to start-2-backend.ps1: DEMO mode — no API key, no proxy, $0.
# Rule-based canned reasoning, but every tool runs for real (live SQL, real
# reports, real workflows). Perfect for the first run and for testing.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "backend")

if (-not (Test-Path ".venv")) {
    Write-Host "First run: creating the Python environment (one-time)..." -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
    else { & python -m venv .venv }
}
& .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
& .venv\Scripts\python.exe scripts\seed.py

$env:DEMO_MODE = "1"

Write-Host ""
Write-Host "Backend starting in DEMO mode on http://localhost:8000 - keep this window open." -ForegroundColor Green
& .venv\Scripts\uvicorn.exe app.main:app --port 8000
