$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "WSL DNS Setup for Codex Device Auth" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Configuring /etc/wsl.conf..." -ForegroundColor Cyan
wsl bash -c "sudo bash -c 'cat > /etc/wsl.conf << EOF
[boot]
systemd=true
[user]
default=fedor
[network]
generateResolvConf = false
EOF'"
Write-Host "Done with wsl.conf" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Configuring /etc/resolv.conf..." -ForegroundColor Cyan
wsl bash -c "sudo bash -c 'cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF'"
Write-Host "Done with resolv.conf" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Protecting /etc/resolv.conf..." -ForegroundColor Cyan
wsl bash -c "sudo chattr +i /etc/resolv.conf"
Write-Host "Done with protection" -ForegroundColor Green
Write-Host ""

Write-Host "DNS Setup Complete" -ForegroundColor Green
Write-Host "Restart WSL and test: codex login --device-auth" -ForegroundColor Yellow