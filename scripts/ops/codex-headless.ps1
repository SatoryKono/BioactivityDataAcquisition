#!/usr/bin/env pwsh
# Codex for Headless Machine (No MCP servers)
# Usage: .\scripts\ops\codex-headless.ps1

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex Headless Mode (No MCP Servers)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = (Get-Location).Path
$repoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"

Write-Host "[setup] Repository: $repoRoot" -ForegroundColor Cyan
Write-Host "[setup] Mode: Headless (no MCP servers)" -ForegroundColor Green
Write-Host "[setup] Launching Codex..." -ForegroundColor Green
Write-Host ""

# Run Codex headless with interactive terminal
wsl -e bash "$repoWSL/scripts/ops/codex-headless.sh" 2>&1

exit $LASTEXITCODE
