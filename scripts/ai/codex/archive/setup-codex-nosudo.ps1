#!/usr/bin/env pwsh
# Codex Setup (No Sudo) — PowerShell Launcher
# Usage: .\scripts\ops\setup-codex-nosudo.ps1

param(
    [switch]$Pause = $true
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex WSL Setup (No Sudo Required)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Get repo root
$repoRoot = (Get-Location).Path
Write-Host "[setup] Repository: $repoRoot" -ForegroundColor Cyan

# Convert path
$repoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
Write-Host "[setup] WSL Path: $repoWSL" -ForegroundColor Cyan
Write-Host ""

Write-Host "[setup] This setup does NOT require sudo password" -ForegroundColor Green
Write-Host "[setup] Installing Node packages... (this may take 2-3 minutes)" -ForegroundColor Green
Write-Host ""

# Run setup and capture all output
$output = wsl bash "$repoWSL/scripts/ops/setup-wsl-codex-nosudo.sh" 2>&1
$exitCode = $LASTEXITCODE

# Display output
Write-Host $output

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  Setup Complete! (C)" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "  1. Test Codex:"
    Write-Host "     .\scripts\ops\codex.bat 'analyze the pipeline'"
    Write-Host ""
    Write-Host "  2. Or interactive:"
    Write-Host "     .\scripts\ops\codex.bat"
    Write-Host ""
    Write-Host "  3. For more options:"
    Write-Host "     .\scripts\ops\codex.bat --help"
    Write-Host ""
}
else {
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host "  Setup Complete with Notes" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Status: Exit code $exitCode" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try testing Codex:" -ForegroundColor Yellow
    Write-Host "  .\scripts\ops\codex.bat 'hello'"
    Write-Host ""
    Write-Host "If errors, try:" -ForegroundColor Yellow
    Write-Host "  1. Open WSL: wsl"
    Write-Host "  2. Check: npm --version"
    Write-Host "  3. Check: ~/.cache/tools/codex-cli/npm-global/bin/codex --version"
    Write-Host ""
}

if ($Pause) {
    Read-Host "Press Enter to exit"
}

exit $exitCode
