#!/usr/bin/env pwsh
# Canonical Codex setup verification launcher.

param(
    [switch]$Pause = $true
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex Setup Verification" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Write-Host "[verify] Repository: $repoRoot"
Write-Host ""

Write-Host "[verify] Checking WSL availability..."
try {
    $wslTest = wsl --list 2>$null
    if ($?) {
        Write-Host "[OK] WSL is available" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] WSL not responding" -ForegroundColor Red
        if ($Pause) { Read-Host "Press Enter to exit" }
        exit 1
    }
} catch {
    Write-Host "[ERROR] WSL not found. Ensure WSL2 is installed." -ForegroundColor Red
    if ($Pause) { Read-Host "Press Enter to exit" }
    exit 1
}
Write-Host ""

Write-Host "[verify] Converting paths for WSL..."
try {
    $repoWSL = wsl wslpath -a $repoRoot 2>&1
    if ($LASTEXITCODE -eq 0 -and $repoWSL -and -not ($repoWSL -match "Error|error")) {
        Write-Host "[OK] Repository path: $repoWSL" -ForegroundColor Green
    } else {
        $drive = $repoRoot.Substring(0, 1).ToLower()
        $pathPart = $repoRoot.Substring(2).Replace('\', '/')
        $repoWSL = "/mnt/$drive$pathPart"
        Write-Host "[OK] Repository path: $repoWSL (constructed)" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] Path conversion failed: $_" -ForegroundColor Red
    if ($Pause) { Read-Host "Press Enter to exit" }
    exit 1
}
Write-Host ""

Write-Host "[verify] Running diagnostic tool..."
Write-Host ""

try {
    wsl bash "$repoWSL/scripts/ai/codex/diagnose_wsl.sh" 2>&1
    $diagExit = $LASTEXITCODE
} catch {
    Write-Host "[ERROR] Failed to run diagnostics: $_" -ForegroundColor Red
    $diagExit = 1
}

Write-Host ""
if ($diagExit -eq 0) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  All Checks Passed! System is ready." -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "  1. Run setup if not already done:"
    Write-Host "     .\script-codex\setup-codex-wsl.bat"
    Write-Host ""
    Write-Host "  2. Test Codex:"
    Write-Host "     .\scripts\ops\codex.bat `"analyze the pipeline`""
    Write-Host ""
} else {
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host "  Some Issues Found (see above)" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run setup to fix:" -ForegroundColor Yellow
    Write-Host "  .\script-codex\setup-codex-wsl.bat"
    Write-Host ""
}

if ($Pause) {
    Read-Host "Press Enter to exit"
}

exit $diagExit
