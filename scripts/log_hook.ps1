param(
    [string]$ToolName = ""
)

$ErrorActionPreference = "SilentlyContinue"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = New-Object System.Text.UTF8Encoding $false

function Get-GitValue {
    param([string[]]$ArgsList)
    try {
        $value = & git @ArgsList 2>$null
        if ($LASTEXITCODE -ne 0) { return "" }
        return (($value | Out-String).Trim())
    } catch {
        return ""
    }
}

function Get-Prop {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Default = ""
    )
    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop -or $null -eq $prop.Value) { return $Default }
    return $prop.Value
}

function Convert-ToHashtable {
    param([object]$Object)
    $hash = [ordered]@{}
    foreach ($prop in $Object.PSObject.Properties) {
        $hash[$prop.Name] = $prop.Value
    }
    return $hash
}

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try {
    $data = $raw | ConvertFrom-Json
} catch {
    exit 0
}

$tool = $ToolName.Trim().ToLowerInvariant()
if (-not $tool) {
    $envTool = [Environment]::GetEnvironmentVariable("AI_TOOL_NAME", "Process")
    if ($envTool) {
        $tool = $envTool.Trim().ToLowerInvariant()
    }
}
if (-not $tool) {
    if (Get-Prop $data "transcript_path") {
        $tool = "codex"
    } elseif (Get-Prop $data "hook_event_name") {
        $tool = "unknown"
    } else {
        $tool = "unknown"
    }
}

$event = Get-Prop $data "hook_event_name" (Get-Prop $data "event" "")
$prompt = (Get-Prop $data "prompt" "")
if ($prompt.Length -gt 1000) {
    $prompt = $prompt.Substring(0, 1000)
}

if (-not $prompt -and $event -notin @("Stop", "stop", "SessionEnd", "sessionEnd", "AfterModel")) {
    exit 0
}

$remote = Get-GitValue @("remote", "get-url", "origin")
$repo = ""
if ($remote) {
    $repo = [System.IO.Path]::GetFileNameWithoutExtension($remote.TrimEnd("/"))
}

$entry = [ordered]@{
    ts = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId(
        [datetime]::UtcNow,
        "SE Asia Standard Time"
    ).ToString("yyyy-MM-ddTHH:mm:ss.fffffffzzz")
    tool = $tool
    event = $event
    session_id = (Get-Prop $data "session_id" (Get-Prop $data "conversation_id" (Get-Prop $data "generation_id" "")))
    model = (Get-Prop $data "model" "")
    repo = $repo
    branch = (Get-GitValue @("rev-parse", "--abbrev-ref", "HEAD"))
    commit = (Get-GitValue @("rev-parse", "--short", "HEAD"))
    student = (Get-GitValue @("config", "user.email"))
    prompt = $prompt
}

if ($tool -eq "codex") {
    $entry["turn_id"] = (Get-Prop $data "turn_id" "")
    $entry["transcript_path"] = (Get-Prop $data "transcript_path" "")
} elseif ($tool -eq "copilot") {
    $entry["tool_name"] = (Get-Prop $data "toolName" "")
    $entry["tool_args"] = (Get-Prop $data "toolArgs" $null)
} elseif ($tool -eq "cursor") {
    $entry["files_context"] = (Get-Prop $data "attachments" @())
} elseif ($tool -eq "claude") {
    $entry["tool_name"] = (Get-Prop $data "tool_name" "")
    $entry["tool_input"] = (Get-Prop $data "tool_input" $null)
    $entry["tool_response"] = ((Get-Prop $data "tool_response" "") | Out-String).Substring(0, [Math]::Min(500, ((Get-Prop $data "tool_response" "") | Out-String).Length))
}

$logDir = if ($env:AI_LOG_DIR) { $env:AI_LOG_DIR } else { ".ai-log" }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "session.jsonl"

($entry | ConvertTo-Json -Compress -Depth 20) | Add-Content -Path $logFile -Encoding UTF8

Write-Output '{"status":"logged"}'
