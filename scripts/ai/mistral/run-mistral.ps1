#!/usr/bin/env pwsh
# Compatibility launcher for the canonical scripts/ai/mistrall surface.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CanonicalLauncher = Join-Path (Join-Path (Split-Path $ScriptDir -Parent) "mistrall") "run-mistrall.ps1"

& $CanonicalLauncher @Args
exit $LASTEXITCODE
