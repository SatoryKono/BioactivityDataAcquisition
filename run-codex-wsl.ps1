#!/usr/bin/env pwsh
# Repository root legacy alias over codex.ps1.

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PrimaryRootLauncher = Join-Path $RepoRoot "codex.ps1"

if (-not (Test-Path -LiteralPath $PrimaryRootLauncher)) {
    Write-Error "Primary root Codex launcher not found: $PrimaryRootLauncher"
    exit 1
}

$ArgsList = @($Command)
if ($Prompt.Count -gt 0) {
    $ArgsList += $Prompt
}

& $PrimaryRootLauncher @ArgsList
exit $LASTEXITCODE
