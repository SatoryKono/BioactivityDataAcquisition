#!/usr/bin/env pwsh
# Simplified Codex WSL launcher from repo root

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $RepoRoot "scripts\ai\codex\run-codex.ps1"

if (-not (Test-Path $Launcher)) {
    Write-Error "Codex launcher not found at: $Launcher"
    exit 1
}

& $Launcher @Args
exit $LASTEXITCODE
