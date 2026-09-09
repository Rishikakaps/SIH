$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install Python 3.12 from python.org, including the Windows Python launcher, then retry.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22 LTS (with npm), reopen the terminal, then retry.' }
& py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Install it and retry.' }
& .\.venv\Scripts\python.exe -m pip install --timeout 120 --retries 10 -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed. Check your internet connection and retry.' }
Push-Location frontend
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
& .\.venv\Scripts\python.exe backend\setup_ocr.py
if ($LASTEXITCODE -ne 0) { throw 'OCR model download failed. Run .\.venv\Scripts\python.exe backend\setup_ocr.py to retry. Typed intake still works.' }
Write-Host 'Setup complete. Open start-backend.cmd and start-frontend.cmd, then visit http://localhost:3000'
