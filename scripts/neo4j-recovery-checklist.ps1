#!/usr/bin/env powershell
# Compatibility wrapper: delegates to canonical implementation in scripts/ops/runtime/neo4j/.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DelegateScript = Join-Path $ScriptDir "ops/runtime/neo4j/neo4j-recovery-checklist.ps1"

if (-not (Test-Path $DelegateScript)) {
    Write-Error "[neo4j-recovery-checklist][error] Delegate script not found: $DelegateScript"
}

& $DelegateScript @args
exit $LASTEXITCODE
