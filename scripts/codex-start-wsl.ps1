# Start Codex MCP servers under WSL2
param()

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSCommandPath
$ProjectDir = Split-Path -Parent $ProjectDir

Write-Host "Starting Codex MCP servers under WSL2..." -ForegroundColor Green
Write-Host "Project directory: $ProjectDir"

Set-Location $ProjectDir

# Load .env
if ((Test-Path ".env") -eq $true)
{
    Write-Host "Loading .env..." -ForegroundColor Blue
    $env_lines = Get-Content .env
    foreach ($line in $env_lines)
    {
        if (($line.Length -gt 0) -and ($line[0] -ne '#'))
        {
            $kv = $line -split '=', 2
            if ($kv.Length -eq 2)
            {
                $k = $kv[0].Trim()
                $v = $kv[1].Trim()
                [Environment]::SetEnvironmentVariable($k, $v)
            }
        }
    }
    Write-Host "Loaded .env" -ForegroundColor Green
}

# Create network
$net_result = docker network inspect warp-network 2>&1
if ($LASTEXITCODE -ne 0)
{
    Write-Host "Creating warp-network..." -ForegroundColor Blue
    docker network create warp-network
}

# Start services
Write-Host "Starting services..." -ForegroundColor Blue
docker compose -f docker-compose.codex.yml up -d

Start-Sleep -Seconds 8

Write-Host ""
Write-Host "Status:" -ForegroundColor Cyan
docker ps -f name=bioetl-mcp --format "table {{.Names}}`t{{.Status}}"

Write-Host ""
Write-Host "Codex MCP servers ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Servers running:"
Write-Host "  - bioetl-mcp-memory"
Write-Host "  - bioetl-mcp-filesystem"
Write-Host "  - bioetl-mcp-github"
Write-Host "  - bioetl-mcp-fetch"
Write-Host ""
