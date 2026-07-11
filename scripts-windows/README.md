# Windows one-paste setup

Three PowerShell windows, one script each, in order. Every script is safe to
re-run; first runs do the one-time installs automatically.

| Window | Paste | What it runs |
|---|---|---|
| 1 | `powershell -ExecutionPolicy Bypass -File scripts-windows\start-1-proxy.ps1` | LiteLLM proxy → Gemini (port 4000) |
| 2 | `powershell -ExecutionPolicy Bypass -File scripts-windows\start-2-backend.ps1` | Business OS backend (port 8000) |
| 3 | `powershell -ExecutionPolicy Bypass -File scripts-windows\start-3-frontend.ps1` | Dashboard (http://localhost:3000) |

(`cd` into the project folder first in each window.)

**Your Gemini API key goes in exactly one place:** the file
`gemini-key.txt` in the project root. The proxy script creates it with a
placeholder on first run and tells you to fill it in. Get a free key at
https://aistudio.google.com/apikey. The file is git-ignored — it never
leaves your machine.

**No key yet?** Use `start-2-backend-demo.ps1` instead of
`start-2-backend.ps1` (skip window 1 entirely): full product, canned
reasoning, real tools, $0.
