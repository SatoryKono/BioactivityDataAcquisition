#!/usr/bin/env pwsh
# Codex Device Auth Login for Headless Machine
# Usage: .\scripts\ops\codex-device-login.ps1

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex Device Auth Login (for Headless Machine)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = (Get-Location).Path
$repoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"

Write-Host "[setup] Repository: $repoRoot" -ForegroundColor Cyan
Write-Host "[setup] Starting device auth login..." -ForegroundColor Green
Write-Host ""

# Run device auth in WSL
wsl -d Ubuntu -e bash "$repoWSL/scripts/ops/codex-device-login.sh"

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  Login Successful! (C)" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "  1. Start Codex:"
    Write-Host "     .\scripts\ops\codex.bat"
    Write-Host ""
    Write-Host "  2. Or use directly:"
    Write-Host "     .\scripts\ops\codex.bat 'your prompt'"
    Write-Host ""
}
else {
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host "  Login Issues" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try again or check internet connection" -ForegroundColor Yellow
    Write-Host ""
}

Read-Host "Press Enter to exit"
exit $exitCode
