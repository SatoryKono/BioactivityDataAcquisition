#!/usr/bin/env pwsh
# Compatibility facade for the canonical Codex setup verification launcher.

param(
    [switch]$Pause = $true
)

$Target = Join-Path $PSScriptRoot "..\..\..\ai\codex\run-codex.ps1"
& $Target check
$ExitCode = $LASTEXITCODE
if ($Pause) {
    Write-Host ""
    Read-Host "Press Enter to continue"
}
exit $ExitCode
