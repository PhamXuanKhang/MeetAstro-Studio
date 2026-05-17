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

$ElectronDir = Resolve-Path (Join-Path $PSScriptRoot "..\electron-app")
$InstallerPath = Join-Path $ElectronDir "release\MeetAstro-Setup-$Version.exe"

Push-Location $ElectronDir
try {
    npm ci
    npm run build -- --win --publish never
}
finally {
    Pop-Location
}

if (-not (Test-Path $InstallerPath)) {
    throw "Installer not found at $InstallerPath."
}

$GhToken = $env:RELEASE_REPO_TOKEN
if (-not $GhToken) {
    throw "Set RELEASE_REPO_TOKEN before running this script."
}

$env:GH_TOKEN = $GhToken

try {
    gh release view $Tag --repo $ReleaseRepo *> $null
    if ($LASTEXITCODE -ne 0) {
        gh release create $Tag --repo $ReleaseRepo --title "MeetAstro $Tag" --generate-notes
    }

    gh release upload $Tag $InstallerPath --repo $ReleaseRepo --clobber
}
finally {
    Remove-Item Env:\GH_TOKEN -ErrorAction SilentlyContinue
}

Write-Host "Released $InstallerPath to $ReleaseRepo@$Tag"
