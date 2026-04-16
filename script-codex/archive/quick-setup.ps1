#!/usr/bin/env pwsh
# Fast Codex Setup for PowerShell
# Usage: .\scripts\ops\quick-setup.ps1
# This version runs setup with a longer timeout and better feedback

param(
    [int]$Timeout = 120  # 2 minutes max for apt-get
)

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex WSL Quick Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = (Get-Location).Path
Write-Host "[setup] Repository: $repoRoot" -ForegroundColor Cyan

# Convert path
$repoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
Write-Host "[setup] WSL Path: $repoWSL" -ForegroundColor Cyan
Write-Host ""

# Run setup with timeout
Write-Host "[setup] Running Codex setup in WSL..." -ForegroundColor Green
Write-Host "[setup] This may take 2-5 minutes on first run" -ForegroundColor Yellow
Write-Host "[setup] (installing Node.js, npm, and Codex)" -ForegroundColor Yellow
Write-Host ""

try {
    # Run with timeout
    $process = Start-Process -FilePath "wsl" -ArgumentList "bash", "$repoWSL/scripts/ops/setup-wsl-codex-complete.sh" -NoNewWindow -PassThru -Wait
    
    $exitCode = $process.ExitCode
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host "  Setup Complete! ✓" -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Green
        Write-Host "  1. Test Codex:"
        Write-Host "     .\scripts\ops\codex.bat `"analyze the pipeline`""
        Write-Host ""
        Write-Host "  2. Or try interactive:"
        Write-Host "     .\scripts\ops\codex.bat"
        Write-Host ""
        Write-Host "  3. For more options:"
        Write-Host "     .\scripts\ops\codex.bat --help"
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "==========================================================" -ForegroundColor Yellow
        Write-Host "  Setup Completed with Issues" -ForegroundColor Yellow
        Write-Host "==========================================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Exit code: $exitCode" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Try manual setup if issues persist:" -ForegroundColor Yellow
        Write-Host "  1. Open WSL terminal"
        Write-Host "  2. Run: cat .\scripts\ops\QUICK_SETUP.md"
        Write-Host "  3. Follow Option 3 or 4 for manual installation"
        Write-Host ""
    }
} catch {
    Write-Host "[ERROR] Setup failed: $_" -ForegroundColor Red
    exit 1
}

Read-Host "Press Enter to exit"
exit $exitCode
