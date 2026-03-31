Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../..")
Set-Location $RepoRoot

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $env:TEMP "uv-cache"
}

if (-not $env:UV_LINK_MODE) {
    $env:UV_LINK_MODE = "copy"
}

$PytestArgs = @($args)
$NeedsDefaultFlags = $true

foreach ($Arg in $PytestArgs) {
    if ($Arg -in @("--help", "-h", "--version", "-V")) {
        $NeedsDefaultFlags = $false
        break
    }
}

if ($NeedsDefaultFlags) {
    $PytestArgs = @("--cov=src/bioetl", "--cov-report=term", "-q", "--maxfail=1") + $PytestArgs
}

$WindowsVenvPython = Join-Path $RepoRoot ".venv-win/Scripts/python.exe"
if (Test-Path $WindowsVenvPython) {
    & $WindowsVenvPython -m pytest @PytestArgs
    exit $LASTEXITCODE
}

$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m pytest @PytestArgs
    exit $LASTEXITCODE
}

if ((Test-Path (Join-Path $RepoRoot ".venv")) -or (Test-Path (Join-Path $RepoRoot ".venv-wsl"))) {
    Write-Host "[run_pytest][hint] A WSL/Linux virtualenv was detected. PowerShell should use .venv-win."
    Write-Host "[run_pytest][hint] Bootstrap it with: .\scripts\dev\setup_env_windows.ps1"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python -m pytest @PytestArgs
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pytest @PytestArgs
    exit $LASTEXITCODE
}

Write-Error "[run_pytest][error] Python runtime is not available."
Write-Host "[run_pytest][hint] Install dependencies first:"
Write-Host "  .\scripts\dev\setup_env_windows.ps1"
exit 1
