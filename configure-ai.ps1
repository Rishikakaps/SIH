$ErrorActionPreference = 'Stop'
Write-Host 'Create an API key in your free Groq account at https://console.groq.com/keys'
Write-Host 'Stay on the Free plan to use its free quota. The app never switches to a paid provider.'
Write-Host 'Your key is saved only in backend\.env on this computer. Do not share that file.'
$groqSecret = Read-Host 'Paste your Groq API key (hidden)' -AsSecureString
$groqPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($groqSecret)
try {
    $groqValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($groqPointer)
    if ($groqValue -notmatch '^gsk_[A-Za-z0-9_-]+$') { throw 'That does not look like a Groq API key. Create one at console.groq.com/keys and retry.' }
    $configPath = Join-Path $PSScriptRoot 'backend\.env'
    $configLines = @(if (Test-Path -LiteralPath $configPath) { Get-Content -LiteralPath $configPath | Where-Object { $_ -notmatch '^\s*(GROQ_API_KEY|GROQ_VISION_MODEL)\s*=' } })
    $configLines += "GROQ_API_KEY=$groqValue"
    $configLines += 'GROQ_VISION_MODEL=qwen/qwen3.6-27b'
    [IO.File]::WriteAllLines($configPath, [string[]]$configLines, (New-Object Text.UTF8Encoding($false)))
    Write-Host 'Key saved. Restart the backend and refresh the app. Use Review image with AI on the Review screen.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($groqPointer)
    $groqValue = $null
    $configLines = $null
}
