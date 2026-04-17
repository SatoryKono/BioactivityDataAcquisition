#!/usr/bin/env powershell
# Compatibility wrapper: delegates to canonical implementation in scripts/ops/runtime/docker/.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DelegateScript = Join-Path $ScriptDir "ops/runtime/docker/restart-docker.ps1"

if (-not (Test-Path $DelegateScript)) {
    Write-Error "[restart-docker][error] Delegate script not found: $DelegateScript"
}

& $DelegateScript @args
exit $LASTEXITCODE
