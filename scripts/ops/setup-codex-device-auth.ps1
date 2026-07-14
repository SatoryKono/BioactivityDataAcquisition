#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup Codex login using device authentication flow

.DESCRIPTION
    This script helps configure Codex login via --device-auth.
    It checks network connectivity, VPN status, and provides guidance
    for troubleshooting connection issues with auth.openai.com

.NOTES
    File: setup-codex-device-auth.ps1
    Requires: PowerShell 5.1+, Codex CLI installed via npm
#>

$ErrorActionPreference = "Stop"

Write-Host "=== Codex Device Authentication Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Codex is installed - prefer direct npm installation
$codexDirectPath = "$env:APPDATA\npm\codex.cmd"
$codexPath = $null

if (Test-Path $codexDirectPath) {
    $codexPath = $codexDirectPath
    Write-Host "[OK] Using direct npm Codex at: $codexPath" -ForegroundColor Green
} else {
    $codexPath = Get-Command codex -ErrorAction SilentlyContinue
    if (-not $codexPath) {
        Write-Host "[ERROR] Codex CLI not found in PATH" -ForegroundColor Red
        Write-Host "Install it with: npm install -g @openai/codex" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[OK] Codex CLI found at: $($codexPath.Source)" -ForegroundColor Green
}

# Create a script-level alias for the direct codex path
Set-Alias -Name CodexDirect -Value $codexPath -Scope Script
Write-Host ""

# Check current login status
Write-Host "Checking current login status..." -ForegroundColor Cyan
$loginCheck = & CodexDirect login status 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[INFO] Already logged in: $loginCheck" -ForegroundColor Yellow
    $response = Read-Host "Do you want to logout and re-authenticate with device flow? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Keeping current authentication." -ForegroundColor Green
        exit 0
    }
    & CodexDirect logout
    Write-Host "[OK] Logged out successfully" -ForegroundColor Green
    Write-Host ""
}

# Check VPN status
Write-Host "Checking VPN status..." -ForegroundColor Cyan
$vpnAdapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and ($_.Name -like '*Nord*' -or $_.Name -like '*VPN*' -or $_.Name -like '*Cisco*' -or $_.Name -like '*OpenVPN*') }

if ($vpnAdapters) {
    Write-Host "[WARNING] Active VPN adapter(s) detected:" -ForegroundColor Yellow
    foreach ($adapter in $vpnAdapters) {
        Write-Host "  - $($adapter.Name) ($($adapter.InterfaceDescription))" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "[INFO] VPN may block connection to auth.openai.com" -ForegroundColor Yellow
    Write-Host "[INFO] Consider temporarily disabling VPN or adding OpenAI domains to split tunneling" -ForegroundColor Yellow
    Write-Host ""

    $vpnResponse = Read-Host "Do you want to continue anyway? (y/N)"
    if ($vpnResponse -ne 'y' -and $vpnResponse -ne 'Y') {
        Write-Host "Please disable VPN and run this script again." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] No active VPN adapters detected" -ForegroundColor Green
    Write-Host ""
}

# Test connectivity to auth.openai.com
Write-Host "Testing connectivity to auth.openai.com..." -ForegroundColor Cyan
try {
    $testResult = Test-NetConnection -ComputerName "auth.openai.com" -Port 443 -WarningAction SilentlyContinue -ErrorAction Stop
    if ($testResult.TcpTestSucceeded) {
        Write-Host "[OK] Can connect to auth.openai.com:443" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Cannot connect to auth.openai.com:443" -ForegroundColor Yellow
        Write-Host "[INFO] This may be due to firewall, proxy, or VPN" -ForegroundColor Yellow
        $continueResponse = Read-Host "Continue anyway? (y/N)"
        if ($continueResponse -ne 'y' -and $continueResponse -ne 'Y') {
            exit 1
        }
    }
} catch {
    Write-Host "[WARNING] Connectivity test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "[INFO] Continuing with authentication attempt..." -ForegroundColor Yellow
}
Write-Host ""

# Attempt device authentication
Write-Host "Attempting device authentication..." -ForegroundColor Cyan
Write-Host "[INFO] This will open a browser window for device code verification" -ForegroundColor Cyan
Write-Host ""

try {
    & CodexDirect login --device-auth
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[SUCCESS] Device authentication completed successfully!" -ForegroundColor Green
        Write-Host ""

        # Verify login
        $verifyCheck = & CodexDirect login status 2>&1
        Write-Host "[INFO] Current login status: $verifyCheck" -ForegroundColor Cyan
        Write-Host ""

        # Remind about VPN if it was active
        if ($vpnAdapters) {
            Write-Host "[REMINDER] You had active VPN during authentication" -ForegroundColor Yellow
            Write-Host "[INFO] If you disabled VPN, you can re-enable it now" -ForegroundColor Yellow
            Write-Host "[INFO] Consider adding OpenAI domains to VPN split tunneling:" -ForegroundColor Yellow
            Write-Host "  - auth.openai.com" -ForegroundColor Yellow
            Write-Host "  - api.openai.com" -ForegroundColor Yellow
            Write-Host "  - *.openai.com" -ForegroundColor Yellow
        }

        exit 0
    } else {
        Write-Host ""
        Write-Host "[ERROR] Device authentication failed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
        Write-Host "1. Temporarily disable VPN/firewall" -ForegroundColor Yellow
        Write-Host "2. Check network connectivity: Test-NetConnection auth.openai.com -Port 443" -ForegroundColor Yellow
        Write-Host "3. Try alternative method: echo `$OPENAI_API_KEY | codex login --with-api-key" -ForegroundColor Yellow
        Write-Host "4. Check Codex doctor: codex doctor" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[ERROR] Exception during authentication: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
