$ErrorActionPreference = "Stop"

$ElectronDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoRoot = Resolve-Path (Join-Path $ElectronDir "..")
$SpecPath = Join-Path $ElectronDir "python\recorder_server.spec"
$RequirementsPath = Join-Path $ElectronDir "python\requirements.txt"
$DistDir = Join-Path $ElectronDir "python-dist"
$OutputExe = Join-Path $DistDir "recorder_server\recorder_server.exe"
$VenvDir = Join-Path $ElectronDir ".venv-sidecar"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required to build the recorder sidecar. Install Python 3.11+ and ensure 'python' is on PATH."
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path $VenvPython)) {
        python -m venv $VenvDir
    }

    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r $RequirementsPath pyinstaller

    if (Test-Path $DistDir) {
        Remove-Item $DistDir -Recurse -Force
    }

    & $VenvPython -m PyInstaller --noconfirm --distpath $DistDir --workpath (Join-Path $ElectronDir "python-build") $SpecPath

    if (-not (Test-Path $OutputExe)) {
        throw "Recorder sidecar executable not found at $OutputExe."
    }

    $SmokeScript = @'
import importlib
modules = [
    "numpy",
    "sounddevice",
    "pysysaudio",
    "websocket",
    "pydantic_settings",
    "src.modules.audio_recorder",
]
for module in modules:
    importlib.import_module(module)
print("sidecar import smoke ok")
'@
    $SmokeFile = Join-Path $ElectronDir "python-build\sidecar_import_smoke.py"
    Set-Content -Path $SmokeFile -Value $SmokeScript -Encoding utf8
    $PreviousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = $RepoRoot
        & $VenvPython $SmokeFile
        if ($LASTEXITCODE -ne 0) {
            throw "Recorder sidecar import smoke failed."
        }
    }
    finally {
        $env:PYTHONPATH = $PreviousPythonPath
    }

    Write-Host "Built recorder sidecar at $OutputExe"
}
finally {
    Pop-Location
}
