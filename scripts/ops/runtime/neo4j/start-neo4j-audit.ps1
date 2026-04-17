#!/usr/bin/env powershell
# Start Neo4j audit instance for live validation
# Usage: .\scripts\ops\runtime\neo4j\start-neo4j-audit.ps1

param(
    [switch]$Stop,
    [switch]$Logs
)

$composeFile = "docker-compose.neo4j-audit.yml"
$containerName = "bioetl-neo4j-audit"

if ($Stop) {
    Write-Host "Stopping audit instance..." -ForegroundColor Yellow
    docker compose -f $composeFile down
    Write-Host "Stopped." -ForegroundColor Green
    exit 0
}

if ($Logs) {
    Write-Host "Showing logs..." -ForegroundColor Cyan
    docker logs $containerName --tail 50 -f
    exit 0
}

Write-Host "Starting Neo4j audit instance (1024m heap)..." -ForegroundColor Cyan
docker compose -f $composeFile up -d

Write-Host "Waiting for startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 45

$status = docker ps | Select-String $containerName
if ($status -match "healthy") {
    Write-Host "✅ Audit instance started successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Connection details:" -ForegroundColor Cyan
    Write-Host "  HTTP:  http://localhost:7475"
    Write-Host "  Bolt:  bolt://localhost:7688"
    Write-Host "  Auth:  neo4j / audit_secure_password"
    Write-Host ""
    Write-Host "To run live validation:" -ForegroundColor Cyan
    Write-Host "  live --apply --only-complexity-layer --batch-size 5"
    Write-Host ""
    Write-Host "To view logs:" -ForegroundColor Cyan
    Write-Host "  .\scripts\ops\runtime\neo4j\start-neo4j-audit.ps1 -Logs"
    Write-Host ""
    Write-Host "To stop:" -ForegroundColor Cyan
    Write-Host "  .\scripts\ops\runtime\neo4j\start-neo4j-audit.ps1 -Stop"
} else {
    Write-Host "❌ Instance failed to start. Check logs:" -ForegroundColor Red
    docker logs $containerName | Select-Object -Last 20
    exit 1
}
