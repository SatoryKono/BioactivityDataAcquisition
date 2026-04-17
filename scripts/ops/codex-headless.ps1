#!/usr/bin/env pwsh
# Compatibility facade for the canonical Codex headless launcher.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$Target = Join-Path $PSScriptRoot "..\ai\codex\headless.ps1"
& $Target @Args
exit $LASTEXITCODE
