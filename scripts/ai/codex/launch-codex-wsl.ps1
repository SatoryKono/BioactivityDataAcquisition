#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch Codex through the canonical WSL/Bash launcher (scripts/ai/codex/run-codex.ps1).

.DESCRIPTION
    Thin alias over run-codex.ps1. Resolves the repository path dynamically instead of
    hardcoding drive letters or WSL distro names.

.PARAMETER Command
    Command to run: start, exec, check, setup, mcp-check, mcp-setup, login, device-login, help

.PARAMETER Prompt
    Optional prompt/arguments for exec mode

.EXAMPLE
    .\launch-codex-wsl.ps1 start
    .\launch-codex-wsl.ps1 exec "analyze my code"
    .\launch-codex-wsl.ps1 check
#>

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CanonicalLauncher = Join-Path $ScriptDir "run-codex.ps1"

if (-not (Test-Path -LiteralPath $CanonicalLauncher)) {
    Write-Error "Canonical Codex launcher not found: $CanonicalLauncher"
    exit 1
}

$ArgsList = @($Command)
if ($Prompt.Count -gt 0) {
    $ArgsList += $Prompt
}

if ($env:BIOETL_WSL_DISTRO) {
    Write-Host "Launching Codex via WSL ($($env:BIOETL_WSL_DISTRO))..." -ForegroundColor Cyan
}
else {
    Write-Host "Launching Codex via the default WSL distro..." -ForegroundColor Cyan
}
Write-Host "   Command: $Command" -ForegroundColor Gray

& $CanonicalLauncher @ArgsList
exit $LASTEXITCODE
