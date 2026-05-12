# Compatibility wrapper for the legacy root startup launcher.
# Stable startup script for BioETL + MCP servers
# Usage: .\scripts\startup.ps1 -Environment prod

param(
    [ValidateSet('dev', 'prod')]
    [string]$Environment = 'dev'
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "🚀 Starting BioETL stack (environment: $Environment)..." -ForegroundColor Green

# Create required networks
Write-Host "📡 Ensuring Docker networks exist..."
docker network create warp-network 2>$null
docker network create bioetl-monitoring 2>$null

# Pre-pull images
Write-Host "🔄 Pre-pulling images..."
docker compose -f "$ProjectDir\docker-compose.codex.yml" pull --quiet 2>$null

# Start base infrastructure if production
if ($Environment -eq 'prod') {
    Write-Host "🏗️  Starting production stack..."
    docker compose -f "$ProjectDir\docker-compose.yml" up -d
    Start-Sleep -Seconds 5
}

# Start MCP servers
Write-Host "🤖 Starting MCP servers..."
docker compose -f "$ProjectDir\docker-compose.codex.yml" up -d

# Wait for services
Write-Host "⏳ Waiting for services to stabilize..."
Start-Sleep -Seconds 3

# Health check
Write-Host "✅ Checking service status..."
$containers = @(
    "bioetl-mcp-memory",
    "bioetl-mcp-filesystem", 
    "bioetl-mcp-github",
    "bioetl-mcp-fetch",
    "bioetl-codex-config"
)

$failed = 0
foreach ($container in $containers) {
    $running = docker ps --filter "name=$container" --filter "status=running" --quiet 2>$null
    if ($running) {
        Write-Host "  ✓ $container" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $container (check with: docker logs $container)" -ForegroundColor Red
        $failed++
    }
}

if ($failed -eq 0) {
    Write-Host ""
    Write-Host "✨ All MCP servers are running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Dashboard: http://localhost:9100"
    Write-Host "💾 Memory: bioetl-mcp-memory"
    Write-Host "📁 Filesystem: bioetl-mcp-filesystem"
    Write-Host "🐙 GitHub: bioetl-mcp-github"
    Write-Host ""
    Write-Host "View logs with: docker compose -f docker-compose.codex.yml logs -f"
} else {
    Write-Host ""
    Write-Host "⚠️  $failed service(s) failed to start" -ForegroundColor Yellow
    exit 1
}
