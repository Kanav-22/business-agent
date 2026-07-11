# Window 1 of 3 - the LiteLLM proxy (translates the app's requests to Gemini).
# Your Gemini API key lives in ONE place: gemini-key.txt in the project folder.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host "[1/3] Checking your Gemini key..." -ForegroundColor Cyan
$keyFile = Join-Path $root "gemini-key.txt"
if (-not (Test-Path $keyFile)) {
    "PASTE-YOUR-GEMINI-KEY-HERE" | Out-File $keyFile -Encoding ascii
}
$key = (Get-Content $keyFile -Raw).Trim()
if (-not $key -or $key -eq "PASTE-YOUR-GEMINI-KEY-HERE") {
    Write-Host ""
    Write-Host "ACTION NEEDED:" -ForegroundColor Yellow
    Write-Host "  1. A file named gemini-key.txt exists in: $root" -ForegroundColor Yellow
    Write-Host "  2. Open it with Notepad, delete the placeholder text," -ForegroundColor Yellow
    Write-Host "     paste your Gemini key (starts with AIza...), and save." -ForegroundColor Yellow
    Write-Host "  3. Run this script again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  (Get a free key at https://aistudio.google.com/apikey)" -ForegroundColor Cyan
    exit 1
}
$env:GEMINI_API_KEY = $key

Write-Host "[2/3] Checking Python + the proxy program..." -ForegroundColor Cyan
$venv = Join-Path $root "backend\.venv"
if (-not (Test-Path $venv)) {
    $py = $null
    if (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
    if (-not $py) {
        Write-Host "Python was not found in this window." -ForegroundColor Red
        Write-Host "If you just installed it: close this window, open a NEW PowerShell, try again." -ForegroundColor Yellow
        Write-Host "If not installed yet:  winget install Python.Python.3.12  (then new window)." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "      Creating the Python environment (one-time, ~30s)..." -ForegroundColor Cyan
    if ($py -eq "py") { & py -3 -m venv $venv } else { & python -m venv $venv }
}
$pip = Join-Path $venv "Scripts\pip.exe"
$litellm = Join-Path $venv "Scripts\litellm.exe"
if (-not (Test-Path $litellm)) {
    Write-Host "      Installing the proxy program." -ForegroundColor Cyan
    Write-Host "      FIRST TIME: several minutes of scrolling text. That is NORMAL." -ForegroundColor Yellow
    Write-Host "      Do NOT close this window or press Ctrl+C - let it finish." -ForegroundColor Yellow
    & $pip install "litellm[proxy]"
}

Write-Host ""
Write-Host "[3/3] Proxy running on http://localhost:4000 - KEEP THIS WINDOW OPEN." -ForegroundColor Green
& $litellm --config (Join-Path $root "litellm_config.yaml") --port 4000
