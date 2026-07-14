# Windows DNS Setup Script for Codex Device-Auth
# Must be run as Administrator

# Check for administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Windows DNS Setup for Device-Auth" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get active network adapters
Write-Host "Step 1: Detecting active network adapters..." -ForegroundColor Cyan

$adapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }

if ($adapters.Count -eq 0) {
    Write-Host "ERROR: No active network adapters found" -ForegroundColor Red
    exit 1
}

Write-Host "Found $($adapters.Count) active adapter(s):" -ForegroundColor Green
$adapters | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor White
}

# Use the first active adapter
$adapterName = $adapters[0].Name
Write-Host "Using adapter: $adapterName" -ForegroundColor Yellow
Write-Host ""

# Step 2: Backup current DNS settings
Write-Host "Step 2: Backing up current DNS settings..." -ForegroundColor Cyan

try {
    $currentDNS = Get-DnsClientServerAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue
    if ($currentDNS) {
        $backupFile = "$env:USERPROFILE\dns-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
        $currentDNS | Out-File -FilePath $backupFile
        Write-Host "DNS settings backed up to: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "No current DNS settings found (using DHCP)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not backup DNS settings, continuing..." -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Set new DNS servers
Write-Host "Step 3: Configuring DNS servers..." -ForegroundColor Cyan
Write-Host "Setting DNS to: 8.8.8.8 (Primary), 8.8.4.4 (Secondary)" -ForegroundColor Yellow

try {
    Set-DnsClientServerAddress -InterfaceAlias $adapterName -ServerAddresses @("8.8.8.8", "8.8.4.4") -ErrorAction Stop
    Write-Host "DNS servers configured successfully" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to configure DNS servers" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Verify DNS settings
Write-Host "Step 4: Verifying DNS settings..." -ForegroundColor Cyan

$newDNS = Get-DnsClientServerAddress -InterfaceAlias $adapterName -AddressFamily IPv4
Write-Host "Current DNS servers:" -ForegroundColor Green
$newDNS | ForEach-Object {
    Write-Host "  - $($_.ServerAddresses -join ', ')" -ForegroundColor White
}

Write-Host ""

# Step 5: Test DNS resolution
Write-Host "Step 5: Testing DNS resolution..." -ForegroundColor Cyan

try {
    $testResult = Resolve-DnsName -Name "google.com" -Server "8.8.8.8" -ErrorAction Stop
    Write-Host "DNS resolution successful" -ForegroundColor Green
} catch {
    Write-Host "WARNING: DNS resolution test failed" -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Restart WSL
Write-Host "Step 6: Restarting WSL to apply new DNS settings..." -ForegroundColor Cyan

$restartWSL = Read-Host "Do you want to restart WSL now? (Y/n)"

if ($restartWSL -ne "n" -and $restartWSL -ne "N") {
    Write-Host "Restarting WSL..." -ForegroundColor Yellow
    wsl --shutdown
    Start-Sleep -Seconds 3
    Write-Host "WSL shutdown complete. Please start WSL manually." -ForegroundColor Green
} else {
    Write-Host "Skipping WSL restart. Please restart manually: wsl --shutdown" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DNS Setup Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start WSL: wsl" -ForegroundColor White
Write-Host "2. Test DNS: ping auth.openai.com" -ForegroundColor White
Write-Host "3. Test device-auth: codex login --device-auth" -ForegroundColor White