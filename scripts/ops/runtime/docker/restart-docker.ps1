#!/usr/bin/env powershell
# Docker Desktop Recovery Script

Write-Host "=== Docker Desktop Recovery ===" -ForegroundColor Cyan
Write-Host ""

# Try graceful shutdown first
Write-Host "Attempting graceful Docker shutdown..." -ForegroundColor Yellow
$dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcess) {
    $dockerProcess | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Docker Desktop stopped" -ForegroundColor Green
    Start-Sleep -Seconds 3
} else {
    Write-Host "⚠ Docker Desktop process not found, checking for daemon..." -ForegroundColor Yellow
    $daemonProcess = Get-Process -Name "dockerd" -ErrorAction SilentlyContinue
    if ($daemonProcess) {
        $daemonProcess | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "✓ dockerd daemon stopped" -ForegroundColor Green
        Start-Sleep -Seconds 3
    }
}

# Restart Docker Desktop
Write-Host ""
Write-Host "Relaunching Docker Desktop..." -ForegroundColor Yellow
$dockerPath = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"

if (Test-Path $dockerPath) {
    & $dockerPath
    Write-Host "✓ Docker Desktop launched" -ForegroundColor Green
    Write-Host ""
    Write-Host "⏳ Waiting for Docker daemon to initialize (60 seconds)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
    
    # Test connectivity
    Write-Host ""
    Write-Host "Testing Docker daemon..." -ForegroundColor Yellow
    try {
        $result = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Docker daemon is responsive!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Cyan
            Write-Host "1. docker compose -f docker-compose.neo4j.yml up"
            Write-Host "2. Wait 60 seconds for Neo4j to start"
            Write-Host "3. node test_neo4j_connection.js"
        } else {
            Write-Host "❌ Docker daemon still unresponsive. Please try again in 30 seconds." -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Connection test failed. Docker may still be initializing." -ForegroundColor Red
    }
} else {
    Write-Host "❌ Docker Desktop not found at: $dockerPath" -ForegroundColor Red
    Write-Host "Install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}
