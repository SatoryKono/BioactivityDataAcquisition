#!/usr/bin/env pwsh
# Codex with API Key Authentication
# Usage: .\scripts\ops\codex-login.ps1

param(
    [string]$ApiKey = ""
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Codex with API Key Authentication" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = (Get-Location).Path
$repoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"

# Get API key
if ([string]::IsNullOrEmpty($ApiKey)) {
    Write-Host "[setup] Looking for API key..." -ForegroundColor Cyan
    
    # Check .env.codex
    if (Test-Path ".\.env.codex") {
        Write-Host "[OK] Found .env.codex file" -ForegroundColor Green
        $envContent = Get-Content ".\.env.codex" | Select-String "OPENAI_API_KEY" | Select-Object -First 1
        if ($envContent) {
            Write-Host "[OK] OPENAI_API_KEY found in .env.codex" -ForegroundColor Green
            $ApiKey = "***"  # Don't show the actual key
        }
    }
    
    # Check environment
    if ([string]::IsNullOrEmpty($ApiKey) -and -not [string]::IsNullOrEmpty($env:OPENAI_API_KEY)) {
        Write-Host "[OK] OPENAI_API_KEY found in environment" -ForegroundColor Green
        $ApiKey = "***"
    }
    
    # If still not found, prompt
    if ([string]::IsNullOrEmpty($ApiKey) -or $ApiKey -eq "***") {
        Write-Host ""
        Write-Host "Setup instructions:" -ForegroundColor Yellow
        Write-Host "  1. Get your API key from: https://platform.openai.com/api-keys" -ForegroundColor Yellow
        Write-Host "  2. Create .env.codex file with: OPENAI_API_KEY=sk-..." -ForegroundColor Yellow
        Write-Host "     Or set environment: \$env:OPENAI_API_KEY = 'sk-...'" -ForegroundColor Yellow
        Write-Host ""
        
        if ([string]::IsNullOrEmpty($ApiKey)) {
            Write-Host "[ERROR] OPENAI_API_KEY not found" -ForegroundColor Red
            Write-Host ""
            Write-Host "Quick setup:" -ForegroundColor Yellow
            Write-Host "  \$env:OPENAI_API_KEY = 'your-api-key-here'" -ForegroundColor Yellow
            Write-Host "  .\scripts\ops\codex-login.ps1" -ForegroundColor Yellow
            Write-Host ""
            exit 1
        }
    }
}

Write-Host ""
Write-Host "[setup] Launching Codex..." -ForegroundColor Green
Write-Host ""

# Run Codex with authentication via WSL
wsl bash "$repoWSL/scripts/ops/codex-login.sh" 2>&1

exit $LASTEXITCODE
