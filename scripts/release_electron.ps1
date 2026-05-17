param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [string]$ReleaseRepo = "PhamXuanKhang/MeetAstro-Studio"
)

$ErrorActionPreference = "Stop"

if ($Tag -notmatch '^v\d+\.\d+\.\d+$') {
    throw "Tag must match vX.Y.Z, got '$Tag'."
}

$Version = $Tag.Substring(1)
$PackageJsonPath = Join-Path $PSScriptRoot "..\electron-app\package.json"
$PackageJson = Get-Content $PackageJsonPath -Raw | ConvertFrom-Json

if ($PackageJson.version -ne $Version) {
    throw "Tag version $Version does not match electron-app/package.json version $($PackageJson.version)."
}

$GhToken = $env:RELEASE_REPO_TOKEN
if (-not $GhToken) {
    throw "Set RELEASE_REPO_TOKEN before running this script."
}

$ElectronDir = Resolve-Path (Join-Path $PSScriptRoot "..\electron-app")
$InstallerPath = Join-Path $ElectronDir "release\MeetAstro-Setup-$Version.exe"

Push-Location $ElectronDir
try {
    npm ci
    npm run typecheck
    npm run build:renderer
    npm run build:main
    npx electron-builder --win --publish never
}
finally {
    Pop-Location
}

if (-not (Test-Path $InstallerPath)) {
    throw "Installer not found at $InstallerPath."
}

$Headers = @{
    Authorization = "Bearer $GhToken"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$ApiBase = "https://api.github.com/repos/$ReleaseRepo"
$Release = $null

try {
    $Release = Invoke-RestMethod -Method Get -Uri "$ApiBase/releases/tags/$Tag" -Headers $Headers
}
catch {
    $StatusCode = $_.Exception.Response.StatusCode.value__
    if ($StatusCode -ne 404) {
        throw
    }
}

if (-not $Release) {
    $CreateBody = @{
        tag_name = $Tag
        name = "MeetAstro $Tag"
        generate_release_notes = $true
    } | ConvertTo-Json
    $Release = Invoke-RestMethod -Method Post -Uri "$ApiBase/releases" -Headers $Headers -Body $CreateBody -ContentType "application/json"
}

$AssetName = Split-Path $InstallerPath -Leaf
foreach ($Asset in $Release.assets) {
    if ($Asset.name -eq $AssetName) {
        Invoke-RestMethod -Method Delete -Uri "$ApiBase/releases/assets/$($Asset.id)" -Headers $Headers | Out-Null
        break
    }
}

$UploadUrl = "https://uploads.github.com/repos/$ReleaseRepo/releases/$($Release.id)/assets?name=$AssetName"
Invoke-RestMethod -Method Post -Uri $UploadUrl -Headers $Headers -InFile $InstallerPath -ContentType "application/octet-stream" | Out-Null

Write-Host "Released $InstallerPath to $ReleaseRepo@$Tag"
