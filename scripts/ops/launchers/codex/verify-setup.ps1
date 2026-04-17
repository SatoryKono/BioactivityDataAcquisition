#!/usr/bin/env pwsh
# Compatibility facade for the canonical Codex setup verification launcher.

param(
    [switch]$Pause = $true
)

$Target = Join-Path $PSScriptRoot "..\..\..\ai\codex\verify_setup.ps1"
& $Target -Pause:$Pause
exit $LASTEXITCODE
