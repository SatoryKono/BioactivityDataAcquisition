Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 @args
    exit $LASTEXITCODE
}

$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 @args
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pytest --cov=src/bioetl --cov-report=term -q --maxfail=1 @args
    exit $LASTEXITCODE
}

Write-Error "[run_pytest][error] Python runtime is not available. Install dependencies first: uv sync --extra dev --extra tests --extra tracing"
