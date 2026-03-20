Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../..")
Set-Location $RepoRoot

$ArgsList = @($args)
if ($ArgsList.Count -eq 0) {
    $ArgsList = @("--config-file", "pyproject.toml", "--strict", "src/bioetl")
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python -m mypy @ArgsList
    exit $LASTEXITCODE
}

$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m mypy @ArgsList
    exit $LASTEXITCODE
}

$UnixVenvPython = Join-Path $RepoRoot ".venv/bin/python"
if (Test-Path $UnixVenvPython) {
    & $UnixVenvPython -m mypy @ArgsList
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m mypy @ArgsList
    exit $LASTEXITCODE
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 -m mypy @ArgsList
    exit $LASTEXITCODE
}

Write-Error "[run_mypy][error] Python runtime is not available."
Write-Host "[run_mypy][hint] Install dependencies first:"
Write-Host "  uv sync --extra dev --extra tracing"
exit 1
