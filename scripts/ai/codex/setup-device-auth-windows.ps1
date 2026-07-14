#!/usr/bin/env pwsh
# Alternative device-auth setup through Windows (when WSL DNS fails)

param(
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Codex Device Auth Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Codex CLI is installed in Windows
Write-Host "Step 1: Checking Codex CLI in Windows..." -ForegroundColor Cyan
try {
    $codexCheck = npm list -g @openai/codex 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK - Codex CLI found via npm" -ForegroundColor Green
    } else {
        Write-Host "ERROR - Codex CLI not found in Windows" -ForegroundColor Red
        Write-Host "Please install: npm install -g @openai/codex" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "ERROR - Codex CLI not found in Windows" -ForegroundColor Red
    Write-Host "Please install: npm install -g @openai/codex" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Function to run codex commands
function Invoke-Codex {
    param([string[]]$Arguments)
    $output = npm exec -y @openai/codex -- $Arguments 2>&1
    return $output
}

# Check current login status
Write-Host "Step 2: Checking current login status..." -ForegroundColor Cyan
try {
    $loginStatus = Invoke-Codex -Arguments @("login", "status")
    Write-Host $loginStatus -ForegroundColor White
} catch {
    Write-Host "Could not check login status" -ForegroundColor Yellow
    $loginStatus = ""
}
Write-Host ""

# If already logged in, ask for confirmation
if ($loginStatus -match "Logged in") {
    if (-not $Force) {
        Write-Host "You are already logged in to Codex." -ForegroundColor Yellow
        $response = Read-Host "Do you want to re-authenticate? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "Setup cancelled." -ForegroundColor Yellow
            exit 0
        }
    }
    Write-Host "Logging out first..." -ForegroundColor Yellow
    try {
        Invoke-Codex -Arguments @("logout")
    } catch {
        Write-Host "Logout failed, continuing..." -ForegroundColor Yellow
    }
}

# Perform device-auth
Write-Host "Step 3: Starting device authentication..." -ForegroundColor Cyan
Write-Host "This will open a browser window for authentication." -ForegroundColor Yellow
Write-Host ""

try {
    $authOutput = Invoke-Codex -Arguments @("login", "--device-auth")
    Write-Host $authOutput -ForegroundColor White

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "SUCCESS - Device authentication completed!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "ERROR - Device authentication failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "ERROR - Device authentication failed with error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Copy credentials to WSL
Write-Host "Step 4: Copying credentials to WSL..." -ForegroundColor Cyan

$wslUser = wsl whoami
$windowsCredPath = "$env:USERPROFILE\.codex"
$wslCredPath = "/home/$wslUser/.codex"

if (Test-Path $windowsCredPath) {
    Write-Host "Copying credentials from Windows to WSL..." -ForegroundColor Yellow

    try {
        wsl mkdir -p $wslCredPath

        Get-ChildItem -Path $windowsCredPath -File | ForEach-Object {
            $destPath = "$wslCredPath/$($_.Name)"
            wsl cp "/mnt/c/Users/$env:USERNAME/.codex/$($_.Name)" $destPath
        }

        Write-Host "OK - Credentials copied to WSL" -ForegroundColor Green
    } catch {
        Write-Host "WARNING - Could not copy credentials to WSL" -ForegroundColor Yellow
        Write-Host "You may need to copy them manually" -ForegroundColor Yellow
    }
} else {
    Write-Host "WARNING - No credentials directory found in Windows" -ForegroundColor Yellow
}

Write-Host ""

# Verify login in WSL
Write-Host "Step 5: Verifying login in WSL..." -ForegroundColor Cyan
try {
    $wslLoginStatus = wsl codex login status 2>&1
    Write-Host $wslLoginStatus -ForegroundColor White

    if ($wslLoginStatus -match "Logged in") {
        Write-Host ""
        Write-Host "SUCCESS - Login verified in WSL!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "WARNING - Login not verified in WSL" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not verify login in WSL" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Device Auth Setup Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now use Codex from both Windows and WSL." -ForegroundColor Green
