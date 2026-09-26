#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch Gemini through the canonical WSL/Bash launcher.

.DESCRIPTION
    Thin alias over run-gemini.ps1. Resolves the repository path dynamically and
    supports BIOETL_WSL_DISTRO for selecting a non-default WSL distribution.

.PARAMETER Command
    Command to run: start, prompt, exec, check, setup, mcp-check, mcp-setup, update, help

.PARAMETER Prompt
    Optional prompt/arguments for prompt or exec mode.

.EXAMPLE
    .\launch-gemini-wsl.ps1 start
    .\launch-gemini-wsl.ps1 exec "review the current diff"
    .\launch-gemini-wsl.ps1 check
#>

param(
    [string]$Command = "start",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CanonicalLauncher = Join-Path $ScriptDir "run-gemini.ps1"

if (-not (Test-Path -LiteralPath $CanonicalLauncher)) {
    Write-Error "Canonical Gemini launcher not found: $CanonicalLauncher"
    exit 1
}

$ArgsList = @($Command)
if ($Prompt.Count -gt 0) {
    $ArgsList += $Prompt
}

if ($env:BIOETL_WSL_DISTRO) {
    Write-Host "Launching Gemini via WSL ($($env:BIOETL_WSL_DISTRO))..." -ForegroundColor Cyan
}
else {
    Write-Host "Launching Gemini via the default WSL distro..." -ForegroundColor Cyan
}
Write-Host "   Command: $Command" -ForegroundColor Gray

& $CanonicalLauncher @ArgsList
exit $LASTEXITCODE
