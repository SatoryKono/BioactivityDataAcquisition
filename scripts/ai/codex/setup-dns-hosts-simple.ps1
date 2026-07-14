# Simple DNS setup via hosts file

$ErrorActionPreference = "Stop"

Write-Host "Adding auth.openai.com to /etc/hosts..." -ForegroundColor Cyan

# Use wsl to add to hosts file
wsl bash -c "echo '104.18.41.241 auth.openai.com' | sudo tee -a /etc/hosts"

Write-Host "Done. Testing connection..." -ForegroundColor Green
wsl ping -c 1 auth.openai.com

Write-Host "Now try: codex login --device-auth" -ForegroundColor Yellow