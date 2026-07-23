#Requires -Version 5.1
<#
.SYNOPSIS
  Bring Docker Desktop + BioETL default stacks up in a crash-resistant way.

.DESCRIPTION
  Root causes of repeated Desktop dies on this host class:
    - host free RAM exhausted (WSL 16G + IDE + multi-stack rebuilds)
    - simultaneous compose --build / multi-stack up
    - leftover monitoring + neo4j + main contending for memory

  This script:
    1) checks host free RAM (warns / soft-fails if critically low)
    2) starts Docker Desktop and waits until docker info is stable twice
    3) ensures external networks
    4) starts ONLY main (no --build) and optionally neo4j
    5) never starts monitoring unless -WithMonitoring is set
    6) never runs prune / down -v

.EXAMPLE
  .\scripts\ops\runtime\docker\ensure-stable.ps1
  .\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j
  .\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl
#>
[CmdletBinding()]
param(
    [switch]$WithNeo4j,
    [switch]$WithMonitoring,
    [switch]$RestartWsl,
    [int]$MinFreeGb = 3,
    [int]$EngineWaitMinutes = 5
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

function Get-HostFreeGb {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round($os.FreePhysicalMemory / 1MB, 1)
}

function Test-DockerStable {
    $v1 = docker info --format '{{.ServerVersion}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $v1) { return $false }
    Start-Sleep -Seconds 12
    $v2 = docker info --format '{{.ServerVersion}}' 2>$null
    return ($LASTEXITCODE -eq 0 -and $v2)
}

function Ensure-Env {
    if (-not $env:LOG_LEVEL) { $env:LOG_LEVEL = 'INFO' }
    if (-not $env:NEO4J_USERNAME) { $env:NEO4J_USERNAME = 'neo4j' }
    if (-not $env:NEO4J_PASSWORD -and (Test-Path (Join-Path $Root '.env'))) {
        Get-Content (Join-Path $Root '.env') | ForEach-Object {
            if ($_ -match '^\s*NEO4J_PASSWORD=(.*)$') {
                $env:NEO4J_PASSWORD = $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
}

$free = Get-HostFreeGb
Write-Host "Host free RAM: ${free} GiB (min recommended: $MinFreeGb GiB)"
if ($free -lt $MinFreeGb) {
    Write-Warning @"
Free RAM is critically low (${free} GiB). Docker Desktop / WSL often dies here.
Close heavy apps (IDE indexers, browsers) or lower WSL memory in %USERPROFILE%\.wslconfig,
then re-run. Continuing best-effort...
"@
}

if ($RestartWsl) {
    Write-Host 'Restarting WSL (releases vmmem; briefly interrupts Ubuntu)...'
    wsl --shutdown 2>$null
    Start-Sleep -Seconds 8
}

Write-Host 'Starting Docker Desktop...'
Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -ErrorAction SilentlyContinue

$deadline = (Get-Date).AddMinutes($EngineWaitMinutes)
$ready = $false
while ((Get-Date) -lt $deadline) {
    if (Test-DockerStable) {
        $ver = docker info --format '{{.ServerVersion}}' 2>$null
        Write-Host "ENGINE STABLE $ver"
        $ready = $true
        break
    }
    Write-Host 'waiting for engine...'
    Start-Sleep -Seconds 8
}
if (-not $ready) {
    Write-Error 'Docker engine did not become stable. Try: wsl --shutdown, free RAM, re-run with -RestartWsl.'
    exit 1
}

Ensure-Env
foreach ($net in @('bioetl-runtime', 'bioetl-monitoring')) {
    docker network inspect $net 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        docker network create --label bioetl.owner=ensure-stable $net | Out-Null
        Write-Host "created network $net"
    }
}

Write-Host 'Starting main stack (no rebuild)...'
docker compose -p bioetl-main -f docker-compose.yml up -d --no-build 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'main up failed; if image missing, build once only: docker compose -p bioetl-main -f docker-compose.yml build bioetl'
}

if ($WithNeo4j) {
    if (-not $env:NEO4J_PASSWORD) {
        Write-Warning 'NEO4J_PASSWORD missing; skip neo4j'
    } else {
        Write-Host 'Starting neo4j (optional helper)...'
        docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d 2>&1 | Out-Host
    }
}

if ($WithMonitoring) {
    Write-Host 'Starting monitoring (opt-in)...'
    docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml up -d --no-build 2>&1 | Out-Host
} else {
    # Soft-stop leftover monitoring containers if present (volumes kept).
    foreach ($name in @('bioetl-prometheus', 'bioetl-pushgateway', 'bioetl-grafana', 'bioetl-monitoring-renderer-1')) {
        $st = docker inspect --format '{{.State.Running}}' $name 2>$null
        if ($st -eq 'true') {
            Write-Host "Stopping leftover monitoring container $name (volumes kept)..."
            docker stop $name 2>$null | Out-Null
        }
    }
}

Start-Sleep -Seconds 20
Write-Host '=== status ==='
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
try {
    $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/ready -TimeoutSec 5
    Write-Host "ready=$($r.StatusCode)"
} catch {
    Write-Warning "ready probe: $($_.Exception.Message)"
}

$freeAfter = Get-HostFreeGb
Write-Host "Host free RAM after start: ${freeAfter} GiB"
Write-Host @'

Stability rules:
  - Prefer:  .\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j
  - Never thrash: avoid repeated docker compose ... --build / --force-recreate
  - One stack at a time; monitoring is opt-in only
  - If engine dies: free RAM, then  .\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl
'@
