# Window 3 of 3 - the dashboard. Needs the backend running (window 2).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "frontend")

Write-Host "[1/2] Checking the dashboard packages..." -ForegroundColor Cyan
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm (Node.js) was not found in this window." -ForegroundColor Red
    Write-Host "If you just installed Node: close this window, open a NEW PowerShell, try again." -ForegroundColor Yellow
    Write-Host "If not installed yet:  winget install OpenJS.NodeJS.LTS  (then new window)." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path "node_modules")) {
    Write-Host "      FIRST TIME: downloading packages, several minutes. That is NORMAL." -ForegroundColor Yellow
    Write-Host "      Do NOT close this window or press Ctrl+C - let it finish." -ForegroundColor Yellow
    npm install --no-audit --no-fund
}

Write-Host ""
Write-Host "[2/2] Dashboard starting - when you see 'Ready', open http://localhost:3000" -ForegroundColor Green
npm run dev
