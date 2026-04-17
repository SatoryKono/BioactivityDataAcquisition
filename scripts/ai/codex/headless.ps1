#!/usr/bin/env pwsh
# Canonical Codex headless launcher from Windows (via WSL).

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Continue"

if ($Args.Count -gt 0 -and ($Args[0] -eq "--help" -or $Args[0] -eq "-h")) {
    Write-Host "Codex Headless Mode (No MCP Servers)"
    Write-Host ""
    Write-Host "Usage: .\headless.ps1 [args...]"
    exit 0
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$RepoWSL = wsl wslpath -a $RepoRoot 2>$null

if (-not $RepoWSL) {
    Write-Host "[ERROR] Failed to convert repository path to WSL" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex Headless Mode (No MCP Servers)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[setup] Repository: $RepoRoot" -ForegroundColor Cyan
Write-Host "[setup] Mode: Headless (no MCP servers)" -ForegroundColor Green
Write-Host "[setup] Launching Codex..." -ForegroundColor Green
Write-Host ""

wsl -e bash "$RepoWSL/scripts/ai/codex/headless.sh" @Args 2>&1
exit $LASTEXITCODE
