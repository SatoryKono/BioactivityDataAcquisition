# Setup DNS via hosts file for device-auth

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DNS Setup via /etc/hosts" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get IP addresses for auth.openai.com
Write-Host "Resolving auth.openai.com..." -ForegroundColor Cyan
$dnsResult = Resolve-DnsName -Name auth.openai.com -DnsOnly -Server 8.8.8.8 -ErrorAction SilentlyContinue

if ($dnsResult) {
    $ipAddresses = $dnsResult | Where-Object { $_.Type -eq 'A' } | Select-Object -First 1 -ExpandProperty IP4Address
    Write-Host "Found IP: $ipAddresses" -ForegroundColor Green
} else {
    Write-Host "Using known IP addresses for auth.openai.com" -ForegroundColor Yellow
    $ipAddresses = "104.18.41.241"
}

Write-Host ""
Write-Host "Adding entry to /etc/hosts in WSL..." -ForegroundColor Cyan

$hostsEntry = "$ipAddresses auth.openai.com"
$hostsFile = "/etc/hosts"

# Create a temporary script to add to hosts
$tempScript = "/tmp/add_hosts.sh"
$scriptContent = @"
echo '$hostsEntry' | sudo tee -a /etc/hosts
"@

# Write the script to WSL
$scriptContent | wsl tee $tempScript > $null

# Make it executable and run
wsl bash -c "chmod +x $tempScript && sudo $tempScript"

# Clean up
wsl rm $tempScript

Write-Host ""
Write-Host "Verifying /etc/hosts..." -ForegroundColor Cyan
wsl cat /etc/hosts | Select-String "auth.openai.com"

Write-Host ""
Write-Host "Testing DNS resolution..." -ForegroundColor Cyan
wsl ping -c 1 -W 2 auth.openai.com

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DNS Setup Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now try device-auth:" -ForegroundColor Yellow
Write-Host "  codex login --device-auth" -ForegroundColor White