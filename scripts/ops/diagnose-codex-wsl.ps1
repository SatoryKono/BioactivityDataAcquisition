# Compatibility facade for the canonical Codex WSL diagnostic launcher.

param(
    [switch]$Verbose = $false
)

$Target = Join-Path $PSScriptRoot "..\ai\codex\diagnose_wsl.ps1"
& $Target -Verbose:$Verbose
exit $LASTEXITCODE
