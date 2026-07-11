# Window 3 of 3 — the dashboard. Needs the backend running (window 2).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "frontend")

if (-not (Test-Path "node_modules")) {
    Write-Host "First run: installing the dashboard packages (one-time, a few minutes)..." -ForegroundColor Cyan
    npm install --no-audit --no-fund
}

Write-Host ""
Write-Host "Dashboard starting - open http://localhost:3000 in your browser." -ForegroundColor Green
npm run dev
