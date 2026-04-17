#!/usr/bin/env pwsh
# Compatibility wrapper for the canonical Vibe launcher.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$Target = Join-Path $PSScriptRoot "ai\vibe\launch.ps1"
& $Target @Args
exit $LASTEXITCODE
