# Window 2 of 3 - the Business OS backend, running on Gemini via the proxy.
# Start scripts-windows/start-1-proxy.ps1 in another window FIRST.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "backend")

Write-Host "[1/4] Checking Python..." -ForegroundColor Cyan
$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
if (-not $py) {
    Write-Host "Python was not found in this window." -ForegroundColor Red
    Write-Host "If you just installed it: close this window, open a NEW PowerShell, try again." -ForegroundColor Yellow
    Write-Host "If not installed yet:  winget install Python.Python.3.12  (then new window)." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path ".venv")) {
    Write-Host "      Creating the Python environment (one-time, ~30s)..." -ForegroundColor Cyan
    if ($py -eq "py") { & py -3 -m venv .venv } else { & python -m venv .venv }
}

Write-Host "[2/4] Installing/checking packages." -ForegroundColor Cyan
Write-Host "      FIRST TIME: several minutes of scrolling text. That is NORMAL." -ForegroundColor Yellow
Write-Host "      Do NOT close this window or press Ctrl+C - let it finish." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "[3/4] Preparing the database..." -ForegroundColor Cyan
& .venv\Scripts\python.exe scripts\seed.py

# --- point the app at the proxy (your key stays in gemini-key.txt) ------------
$env:ANTHROPIC_BASE_URL = "http://localhost:4000"
$env:ANTHROPIC_API_KEY  = "proxy-holds-the-real-key"
$env:AGENT_MODEL        = "business-os"
$env:WEB_TOOLS_ENABLED  = "0"   # Gemini can't run Anthropic's server-side web tools
$env:SURVIVAL_MODE      = "1"   # weak-model scaffolding on

Write-Host ""
Write-Host "[4/4] Backend running on http://localhost:8000 - KEEP THIS WINDOW OPEN." -ForegroundColor Green
& .venv\Scripts\uvicorn.exe app.main:app --port 8000
