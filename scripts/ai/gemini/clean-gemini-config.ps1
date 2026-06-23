#!/usr/bin/env pwsh
# Clean Gemini CLI configuration

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\.."))

Write-Host "Cleaning Gemini CLI configuration..." -ForegroundColor Yellow

# Remove local .gemini directory
if (Test-Path "$RepoRoot\.gemini") {
    Write-Host "Removing $RepoRoot\.gemini" -ForegroundColor Cyan
    Remove-Item -Path "$RepoRoot\.gemini" -Recurse -Force
}

# Remove Gemini CLI cache
if (Test-Path "$RepoRoot\.cache\tools\gemini-cli") {
    Write-Host "Removing $RepoRoot\.cache\tools\gemini-cli" -ForegroundColor Cyan
    Remove-Item -Path "$RepoRoot\.cache\tools\gemini-cli" -Recurse -Force
}

Write-Host "Configuration cleaned successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run: .venv-win\Scripts\python.exe scripts/ai/codex/setup_mcp.py --root . --workspace-root . --skip-codex --skip-codex-config"
Write-Host "2. Run: .\scripts\ai\gemini\run-gemini.ps1"
