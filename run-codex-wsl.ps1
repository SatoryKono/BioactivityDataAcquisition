#!/usr/bin/env pwsh
# Repository root entrypoint: launch Codex through WSL (canonical scripts/ai/codex).

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$CanonicalLauncher = Join-Path $RepoRoot "scripts\ai\codex\run-codex.ps1"

if (-not (Test-Path -LiteralPath $CanonicalLauncher)) {
    Write-Error "Canonical Codex launcher not found: $CanonicalLauncher"
    exit 1
}

$ArgsList = @($Command)
if ($Prompt.Count -gt 0) {
    $ArgsList += $Prompt
}

& $CanonicalLauncher @ArgsList
exit $LASTEXITCODE
