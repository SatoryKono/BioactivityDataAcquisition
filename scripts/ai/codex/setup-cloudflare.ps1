#!/usr/bin/env pwsh
# Cloudflare Tunnel Setup Script for BioETL

param(
    [string]$TunnelName = "bioetl-local",
    [string]$ConfigPath = "config.yml",
    [switch]$SkipLogin = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CloudflaredExe = Join-Path $ScriptDir "cloudflared.exe"

function Test-Cloudflared {
    if (-not (Test-Path $CloudflaredExe)) {
        Write-Host "ERROR: cloudflared.exe not found at $CloudflaredExe" -ForegroundColor Red
        return $false
    }
    return $true
}

function Invoke-CloudflareLogin {
    Write-Host "Step 1: Authorizing with Cloudflare..." -ForegroundColor Cyan
    Write-Host "This will open a browser window for authorization." -ForegroundColor Yellow

    & $CloudflaredExe tunnel login

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Cloudflare login failed" -ForegroundColor Red
        return $false
    }

    Write-Host "✓ Cloudflare login successful" -ForegroundColor Green
    return $true
}

function New-CloudflareTunnel {
    param([string]$Name)

    Write-Host "Step 2: Creating tunnel '$Name'..." -ForegroundColor Cyan

    $output = & $CloudflaredExe tunnel create $Name 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create tunnel" -ForegroundColor Red
        Write-Host $output -ForegroundColor Red
        return $null
    }

    # Extract tunnel ID from output
    $tunnelId = $output | Select-String -Pattern "^[a-f0-9-]{36}$" | Select-Object -First 1
    if ($tunnelId) {
        $tunnelId = $tunnelId.ToString().Trim()
    }

    Write-Host "✓ Tunnel created successfully" -ForegroundColor Green
    Write-Host "Tunnel ID: $tunnelId" -ForegroundColor Yellow

    return $tunnelId
}

function New-TunnelConfig {
    param(
        [string]$TunnelId,
        [string]$ConfigPath
    )

    Write-Host "Step 3: Creating tunnel configuration..." -ForegroundColor Cyan

    $username = $env:USERNAME
    $credPath = "C:\Users\$username\.cloudflared\$TunnelId.json"

    $configContent = @"
tunnel: $TunnelId
credentials-file: $credPath

ingress:
  # Example: Grafana access
  # - hostname: grafana.yourdomain.com
  #   service: http://localhost:3000

  # Example: Prometheus access
  # - hostname: prometheus.yourdomain.com
  #   service: http://localhost:9090

  # Example: Local web application
  # - hostname: bioetl.yourdomain.com
  #   service: http://localhost:8000

  # Fallback for all other requests
  - service: http_status:404
"@

    $configFullPath = Join-Path $ScriptDir $ConfigPath
    $configContent | Out-File -FilePath $configFullPath -Encoding UTF8

    Write-Host "✓ Configuration file created: $configFullPath" -ForegroundColor Green
    Write-Host "Please edit this file to add your specific hostnames and services" -ForegroundColor Yellow

    return $configFullPath
}

function Show-NextSteps {
    param(
        [string]$TunnelId,
        [string]$TunnelName,
        [string]$ConfigPath
    )

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    Write-Host "1. Edit the configuration file:" -ForegroundColor Yellow
    Write-Host "   notepad $ConfigPath" -ForegroundColor White
    Write-Host ""

    Write-Host "2. Add DNS records for each hostname:" -ForegroundColor Yellow
    Write-Host "   .\cloudflared.exe tunnel route dns $TunnelName <hostname>" -ForegroundColor White
    Write-Host ""

    Write-Host "3. Start the tunnel:" -ForegroundColor Yellow
    Write-Host "   .\cloudflared.exe tunnel --config $ConfigPath run $TunnelName" -ForegroundColor White
    Write-Host ""

    Write-Host "4. For production, install as Windows service:" -ForegroundColor Yellow
    Write-Host "   .\cloudflared.exe service install" -ForegroundColor White
    Write-Host ""

    Write-Host "See CLOUDFLARE_SETUP.md for detailed instructions." -ForegroundColor Cyan
}

# Main execution
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cloudflare Tunnel Setup for BioETL" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check cloudflared
if (-not (Test-Cloudflared)) {
    exit 1
}

# Login
if (-not $SkipLogin) {
    if (-not (Invoke-CloudflareLogin)) {
        exit 1
    }
} else {
    Write-Host "Skipping login step (SkipLogin specified)" -ForegroundColor Yellow
}

# Create tunnel
$tunnelId = New-CloudflareTunnel -Name $TunnelName
if (-not $tunnelId) {
    exit 1
}

# Create configuration
$configFullPath = New-TunnelConfig -TunnelId $tunnelId -ConfigPath $ConfigPath
if (-not $configFullPath) {
    exit 1
}

# Show next steps
Show-NextSteps -TunnelId $tunnelId -TunnelName $TunnelName -ConfigPath $configFullPath

Write-Host "`n✓ Setup completed successfully!" -ForegroundColor Green
