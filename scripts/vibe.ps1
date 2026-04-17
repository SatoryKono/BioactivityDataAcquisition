#!/usr/bin/env pwsh
# Compatibility facade for the canonical Vibe launcher.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$Target = Join-Path $PSScriptRoot "ai\vibe\launch.ps1"
& $Target @Args
exit $LASTEXITCODE
