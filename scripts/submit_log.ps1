$ErrorActionPreference = "SilentlyContinue"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = New-Object System.Text.UTF8Encoding $false

function Read-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    foreach ($line in Get-Content $Path) {
        if ($line -match '^\s*#') { continue }
        if ($line -notmatch '^\s*([^=]+?)\s*=\s*(.*)\s*$') { continue }
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

Read-DotEnv ".env"

$serverUrl = $env:AI_LOG_SERVER
$apiKey = $env:AI_LOG_API_KEY
$logDir = if ($env:AI_LOG_DIR) { $env:AI_LOG_DIR } else { ".ai-log" }
$logFile = Join-Path $logDir "session.jsonl"

if (-not $serverUrl) {
    [Console]::Error.WriteLine("[ai-log] AI_LOG_SERVER not set - skipping submission.")
    exit 0
}

if (-not (Test-Path $logFile)) {
    [Console]::Error.WriteLine("[ai-log] No logs to submit.")
    exit 0
}

$entries = @()
foreach ($line in Get-Content $logFile -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $entries += ($line | ConvertFrom-Json)
    } catch {
    }
}

if ($entries.Count -eq 0) {
    [Console]::Error.WriteLine("[ai-log] No valid entries to submit.")
    exit 0
}

$headers = @{}
if ($apiKey) {
    $headers["Authorization"] = "Bearer $apiKey"
}

$payload = @{ entries = $entries } | ConvertTo-Json -Depth 30 -Compress
$payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)

try {
    $response = Invoke-WebRequest `
        -Uri $serverUrl `
        -Method Post `
        -Headers $headers `
        -ContentType "application/json; charset=utf-8" `
        -Body $payloadBytes `
        -TimeoutSec 10 `
        -UseBasicParsing
    [Console]::Error.WriteLine("[ai-log] Submitted $($entries.Count) entries -> $($response.StatusCode)")
} catch {
    $detail = ""
    try {
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $detail = $reader.ReadToEnd()
    } catch {
    }
    if ($detail) {
        [Console]::Error.WriteLine("[ai-log] Submit failed: $($_.Exception.Message) - $detail - logs kept locally.")
    } else {
        [Console]::Error.WriteLine("[ai-log] Submit failed: $($_.Exception.Message) - logs kept locally.")
    }
}

exit 0
