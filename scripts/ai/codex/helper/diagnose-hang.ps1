#!/usr/bin/env pwsh
# Codex Diagnostics - Find where setup hangs
# Usage: .\script-codex\helper\diagnose-hang.ps1

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Codex Setup - Hang Diagnostics" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: WSL connectivity
Write-Host "[1/5] Testing WSL Ubuntu connectivity..." -ForegroundColor Yellow
$wslTest = wsl -d Ubuntu -- echo "WSL working" 2>&1
if ($?) {
    Write-Host "  [OK] WSL Ubuntu is accessible" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] WSL Ubuntu not responding" -ForegroundColor Red
    Write-Host "  Try: wsl --list --running"
    exit 1
}

# Test 2: Bash execution
Write-Host "[2/5] Testing bash execution..." -ForegroundColor Yellow
$bashTest = wsl -d Ubuntu -- bash -c "echo test" 2>&1
if ($?) {
    Write-Host "  [OK] Bash is working" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Bash execution failed" -ForegroundColor Red
    exit 1
}

# Test 3: apt-get update (with timeout and diagnostics)
Write-Host "[3/5] Testing apt-get update (60s timeout)..." -ForegroundColor Yellow
$startTime = Get-Date
$aptTest = wsl -d Ubuntu -- bash -c "timeout 60 sudo apt-get update -qq 2>&1 | head -5" 2>&1
$elapsed = (Get-Date) - $startTime
Write-Host "  Completed in $($elapsed.TotalSeconds)s" -ForegroundColor Cyan
if ($? -or $LASTEXITCODE -lt 2) {
    Write-Host "  [OK] apt-get update responds" -ForegroundColor Green
} else {
    Write-Host "  [WARN] apt-get update exited with code: $LASTEXITCODE" -ForegroundColor Yellow
    Write-Host "  Output: $aptTest" -ForegroundColor Gray
    Write-Host "  This might indicate: apt lock, passwordless sudo issue, or slow network" -ForegroundColor Yellow
}

# Test 4: Node.js check
Write-Host "[4/5] Checking Node.js in WSL..." -ForegroundColor Yellow
$nodeTest = wsl -d Ubuntu -- bash -c "command -v node && node --version || echo 'NOT FOUND'" 2>&1
Write-Host "  Result: $nodeTest" -ForegroundColor Cyan
if ($nodeTest -match "v\d+\.\d+") {
    Write-Host "  [OK] Node.js is installed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Node.js not installed, will need to install" -ForegroundColor Yellow
}

# Test 5: npm install with timeout
Write-Host "[5/5] Testing npm install timeout (30s timeout)..." -ForegroundColor Yellow
Write-Host "  Running: npm install -g cowsay (should complete quickly)" -ForegroundColor Gray
$startTime = Get-Date
$npmTest = wsl -d Ubuntu -- bash -c @"
export NPM_CONFIG_PREFIX=~/.npm-global-test
export NPM_CONFIG_TIMEOUT=10000
timeout 30 npm install -g cowsay 2>&1 | tail -5 || echo "TIMED OUT or FAILED"
"@ 2>&1
$elapsed = (Get-Date) - $startTime
Write-Host "  Completed in $($elapsed.TotalSeconds)s" -ForegroundColor Cyan

if ($npmTest -match "added|TIMED OUT" -or $LASTEXITCODE -eq 0) {
    if ($npmTest -match "TIMED OUT") {
        Write-Host "  [FAIL] npm install TIMED OUT" -ForegroundColor Red
        Write-Host "  This is the likely culprit - npm registry may be slow" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] npm install works" -ForegroundColor Green
    }
} else {
    Write-Host "  [WARN] npm install may have issues" -ForegroundColor Yellow
    Write-Host "  Output: $npmTest" -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTICS COMPLETE" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Green
Write-Host "  • If [5/5] shows timeout: npm registry is slow, increase timeout or use mirror"
Write-Host "  • If [3/5] shows timeout: apt-get issues, check sudo passwordless setup"
Write-Host "  • If [1/5] fails: WSL Ubuntu not running, start it with: wsl -d Ubuntu"
Write-Host ""
