# Compatibility wrapper: delegates to canonical implementation in scripts/dev/.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DelegateScript = Join-Path $ScriptDir "dev/run_pytest.ps1"

if (-not (Test-Path $DelegateScript)) {
    Write-Error "[run_pytest][error] Delegate script not found: $DelegateScript"
}

& $DelegateScript @args
exit $LASTEXITCODE
