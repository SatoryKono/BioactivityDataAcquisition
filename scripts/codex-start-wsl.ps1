# Start Codex MCP servers under WSL2
# Usage: .\scripts\codex-start-wsl.ps1

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSCommandPath | Split-Path -Parent
Write-Host "🚀 Starting Codex MCP servers under WSL2..." -ForegroundColor Green
Write-Host "Project directory: $ProjectDir"

Set-Location $ProjectDir

# Load .env file into environment
if (Test-Path ".env") {
    Write-Host "Loading .env file..." -ForegroundColor Blue
    Get-Content .env | Where-Object { $_ -notmatch '^#' -and $_ -notmatch '^\s*$' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key, $value)
    }
    Write-Host "✓ Loaded .env file" -ForegroundColor Green
} else {
    Write-Host "⚠ .env file not found, using defaults" -ForegroundColor Yellow
}

# Ensure warp-network exists
$networkExists = docker network inspect warp-network 2>$null
if ($null -eq $networkExists) {
    Write-Host "Creating warp-network..." -ForegroundColor Blue
    docker network create warp-network
}

# Start MCP services
Write-Host "Starting MCP servers..." -ForegroundColor Blue
docker compose -f docker-compose.codex.yml up -d

# Wait for startup
Write-Host "Waiting for services to be ready..." -ForegroundColor Blue
Start-Sleep -Seconds 8

# Verify services
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
docker ps -f name=bioetl-mcp --format "table {{.Names}}`t{{.Status}}"

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "✓ Codex MCP servers ready!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "MCP Servers:" -ForegroundColor Cyan
Write-Host "  • Memory:      bioetl-mcp-memory"
Write-Host "  • Filesystem:  bioetl-mcp-filesystem"
Write-Host "  • GitHub:      bioetl-mcp-github"
Write-Host "  • Docker:      bioetl-mcp-docker"
Write-Host ""
Write-Host "Next: Open Anthropic Codex and add MCP servers via settings.json" -ForegroundColor Yellow
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View logs:     docker compose -f docker-compose.codex.yml logs -f"
Write-Host "  Stop servers:  docker compose -f docker-compose.codex.yml down"
Write-Host "  Restart:       docker compose -f docker-compose.codex.yml restart"
Write-Host ""
