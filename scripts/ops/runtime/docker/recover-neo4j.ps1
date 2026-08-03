#Requires -Version 5.1
<#
.SYNOPSIS
  Recover bioetl-neo4j after Docker Desktop / WSL flaps.

.DESCRIPTION
  Run only when `docker info` succeeds and Docker Desktop shows a green/running
  engine. Does not edit .env. Aligns volume auth with NEO4J_PASSWORD from the
  current process environment or existing local .env (read-only).

  Prerequisites:
    - Docker engine reachable
    - NEO4J_PASSWORD available (process env or local .env)
    - External network bioetl-runtime (created if missing)

.EXAMPLE
  .\scripts\ops\runtime\docker\recover-neo4j.ps1
#>
[CmdletBinding()]
param(
    [int]$BootWaitSeconds = 90
)

# Docker CLI writes progress to stderr; do not treat that as a terminating error.
$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

function Test-DockerEngine {
    docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-DockerEngine)) {
    Write-Error @'
Docker engine is not reachable (WSL/Desktop flap).
1) Open Docker Desktop and wait until it is fully running.
2) If you see DockerDesktop/Wsl/CommandTimedOut:
     wsl --shutdown
     then start Docker Desktop again and wait 1-2 minutes.
3) Confirm: docker info
4) Re-run this script.
'@
}

if (-not $env:NEO4J_USERNAME) { $env:NEO4J_USERNAME = 'neo4j' }
if (-not $env:NEO4J_PASSWORD) {
    $envPath = Join-Path $Root '.env'
    if (Test-Path $envPath) {
        Get-Content $envPath | ForEach-Object {
            if ($_ -match '^\s*NEO4J_PASSWORD=(.*)$') {
                $env:NEO4J_PASSWORD = $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
}
if (-not $env:NEO4J_PASSWORD) {
    Write-Error 'NEO4J_PASSWORD is not set in the process environment or local .env'
}

docker network inspect bioetl-runtime 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker network create --label bioetl.owner=neo4j-helper bioetl-runtime | Out-Null
}

Write-Host 'Stopping neo4j (data volume kept)...'
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml stop 2>$null
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml rm -f 2>$null

Write-Host 'Clearing auth/store_lock so NEO4J_AUTH can re-seed (databases kept)...'
# One-shot helper container (not the bioetl-neo4j service owner).
docker run --rm -v bioetl-neo4j_neo4j_data:/data alpine:3.20 `
    sh -c 'rm -f /data/dbms/auth /data/dbms/auth.ini /data/databases/store_lock; echo cleared'

Write-Host 'Starting neo4j...'
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d
Write-Host "Waiting ${BootWaitSeconds}s for boot..."
Start-Sleep -Seconds $BootWaitSeconds

docker ps -a --filter name=bioetl-neo4j --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker logs bioetl-neo4j --tail 30
$health = docker inspect bioetl-neo4j --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
Write-Host "health=$health"

try {
    $code = (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:7474 -TimeoutSec 10).StatusCode
    Write-Host "http://127.0.0.1:7474 -> $code"
} catch {
    Write-Warning "HTTP probe failed: $($_.Exception.Message)"
}

Write-Host 'cypher-shell probe...'
docker exec bioetl-neo4j /var/lib/neo4j/bin/cypher-shell `
    -u neo4j -p $env:NEO4J_PASSWORD 'RETURN 1 AS ok'

if ($health -ne 'healthy') {
    Write-Warning "Container not healthy yet (status=$health). Re-check in ~1 min with:"
    Write-Host '  docker inspect bioetl-neo4j --format "{{.State.Health.Status}}"'
    exit 2
}

Write-Host 'neo4j recover OK'
