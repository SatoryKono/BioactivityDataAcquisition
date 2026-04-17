Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Thin facade for backward compatibility.
# Canonical implementation: scripts/ai/codex/setup_mcp.py

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
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

& $pythonCmd.Source scripts/dev/setup_copilot_codex_mcp.py @args
exit $LASTEXITCODE
