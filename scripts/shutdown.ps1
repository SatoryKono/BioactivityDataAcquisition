# Compatibility wrapper for the legacy root shutdown launcher.
# Graceful shutdown script for BioETL + MCP servers

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "🛑 Stopping BioETL services..." -ForegroundColor Yellow

# Stop MCP servers
Write-Host "Stopping MCP servers..."
docker compose -f "$ProjectDir\docker-compose.codex.yml" down --remove-orphans 2>$null

# Stop base infrastructure
Write-Host "Stopping base infrastructure..."
docker compose -f "$ProjectDir\docker-compose.yml" down --remove-orphans 2>$null

Write-Host "✓ Services stopped gracefully" -ForegroundColor Green
Write-Host ""
Write-Host "To remove all volumes (data cleanup): docker system prune -a"
