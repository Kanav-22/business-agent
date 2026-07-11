# Window 1 of 3 — the LiteLLM proxy (translates the app's requests to Gemini).
# Your Gemini API key lives in ONE place: gemini-key.txt in the project folder.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# --- API key -----------------------------------------------------------------
$keyFile = Join-Path $root "gemini-key.txt"
if (-not (Test-Path $keyFile)) {
    "PASTE-YOUR-GEMINI-KEY-HERE" | Out-File $keyFile -Encoding ascii
}
$key = (Get-Content $keyFile -Raw).Trim()
if (-not $key -or $key -eq "PASTE-YOUR-GEMINI-KEY-HERE") {
    Write-Host ""
    Write-Host "ACTION NEEDED:" -ForegroundColor Yellow
    Write-Host "  1. A file named gemini-key.txt was just created in: $root" -ForegroundColor Yellow
    Write-Host "  2. Open it with Notepad, delete the placeholder text," -ForegroundColor Yellow
    Write-Host "     paste your Gemini key (starts with AIza...), and save." -ForegroundColor Yellow
    Write-Host "  3. Run this script again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  (Get a free key at https://aistudio.google.com/apikey)" -ForegroundColor Cyan
    exit 1
}
$env:GEMINI_API_KEY = $key

# --- Python + LiteLLM inside the backend virtual environment ------------------
$venv = Join-Path $root "backend\.venv"
if (-not (Test-Path $venv)) {
    Write-Host "First run: creating the Python environment (one-time)..." -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $venv }
    else { & python -m venv $venv }
}
$pip = Join-Path $venv "Scripts\pip.exe"
$litellm = Join-Path $venv "Scripts\litellm.exe"
if (-not (Test-Path $litellm)) {
    Write-Host "First run: installing the proxy (one-time, a few minutes)..." -ForegroundColor Cyan
    & $pip install --quiet "litellm[proxy]"
}

Write-Host ""
Write-Host "Proxy starting on http://localhost:4000 — keep this window open." -ForegroundColor Green
& $litellm --config (Join-Path $root "litellm_config.yaml") --port 4000
