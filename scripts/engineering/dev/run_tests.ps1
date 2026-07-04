Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Thin facade for backward compatibility.
# Canonical implementation: scripts/engineering/dev/run_tests.py

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
Set-Location $rootDir

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "[FAIL] Python executable not found in PATH" -ForegroundColor Red
    exit 1
}

& $pythonCmd.Source scripts/engineering/dev/run_tests.py @args
exit $LASTEXITCODE
