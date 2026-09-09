$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'No existing environment here. Run setup-windows.cmd for a fresh installation.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'npm was not found. Install Node.js 22 with npm and reopen the terminal.' }
Write-Host 'Close the running frontend/backend terminals before updating.'
& .\.venv\Scripts\python.exe -m pip install --timeout 120 --retries 10 -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your connection and retry.' }
Push-Location frontend
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
Write-Host 'Update complete. Run configure-ai.cmd to add a Groq key, then start the backend and frontend.'
