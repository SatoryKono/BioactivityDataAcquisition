#Requires -Version 5.1
<#
.SYNOPSIS
  Crash-resistant Docker Desktop + BioETL default stacks (main, optional neo4j).

.DESCRIPTION
  Host-class failure mode (32 GiB Windows + PyCharm + Docker Desktop/WSL):
    free host RAM collapses under multi-stack rebuilds -> docker-desktop WSL
    stops -> npipe dockerDesktopLinuxEngine disappears.

  This script:
    1) soft-fails / warns when free RAM is critically low
    2) optional WSL restart to reclaim vmmem
    3) starts Docker Desktop and requires dual docker info stability
    4) ensures external networks
    5) stops non-BioETL leftover containers (unless -KeepForeignContainers)
    6) starts ONLY main with --no-build; optional neo4j with retry
    7) never starts monitoring unless -WithMonitoring
    8) never prune / down -v

.EXAMPLE
  .\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j
  .\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl -WithNeo4j
#>
[CmdletBinding()]
param(
    [switch]$WithNeo4j,
    [switch]$WithMonitoring,
    [switch]$RestartWsl,
    [switch]$KeepForeignContainers,
    [switch]$SkipHostHarden,
    [int]$MinFreeGb = 4,
    [int]$EngineWaitMinutes = 6
)

$ErrorActionPreference = 'Continue'
$InformationPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

# Apply machine-local Desktop/.wslconfig hardening (no watchdog registration here).
if (-not $SkipHostHarden) {
    $harden = Join-Path $PSScriptRoot 'harden-desktop-host.ps1'
    if (Test-Path $harden) {
        try {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $harden 2>&1 | ForEach-Object { Write-Host $_ }
        } catch {
            Write-Warning "host harden skipped: $($_.Exception.Message)"
        }
    }
}

# Names to keep when stopping foreign containers. Prefix bioetl- also covers
# shared MCP plane containers (bioetl-mcp-*) if Docker path is used later.
$BioetlNames = @(
    'bioetl',
    'bioetl-neo4j',
    'bioetl-grafana',
    'bioetl-prometheus',
    'bioetl-pushgateway',
    'bioetl-monitoring-renderer-1',
    'bioetl-neo4j-audit'
)

function Get-HostFreeGb {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round($os.FreePhysicalMemory / 1MB, 1)
}

function Test-DockerStable {
    $v1 = docker info --format '{{.ServerVersion}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $v1) { return $false }
    Start-Sleep -Seconds 15
    $v2 = docker info --format '{{.ServerVersion}}' 2>$null
    return ($LASTEXITCODE -eq 0 -and [string]$v2 -eq [string]$v1 -and $v2)
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

function Stop-ForeignContainers {
    $rows = docker ps -a --format '{{.Names}}' 2>$null
    if (-not $rows) { return }
    foreach ($name in $rows) {
        $n = [string]$name
        if ([string]::IsNullOrWhiteSpace($n)) { continue }
        $keep = $false
        foreach ($allowed in $BioetlNames) {
            if ($n -eq $allowed -or $n.StartsWith('bioetl-')) { $keep = $true; break }
        }
        if ($keep) { continue }
        Write-Information "Stopping foreign container $n (frees host/WSL RAM)..." -InformationAction Continue
        docker stop $n 2>$null | Out-Null
        # Remove so MCP Toolkit random-name orphans do not accumulate.
        docker rm -f $n 2>$null | Out-Null
    }
    # Explicit MCP pass (labels/images) in case name-based filter missed any.
    $mcpClean = Join-Path $PSScriptRoot 'cleanup-mcp-orphans.ps1'
    if (Test-Path $mcpClean) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $mcpClean 2>&1 |
            ForEach-Object { Write-Information ([string]$_) -InformationAction Continue }
    }
}

function Start-ComposeRetry {
    param(
        # Do NOT name this $Args — that is a PowerShell automatic variable.
        [string[]]$DockerArgs,
        [int]$Attempts = 3
    )
    for ($i = 1; $i -le $Attempts; $i++) {
        # Capture stderr without turning docker progress lines into terminating errors.
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'SilentlyContinue'
        $out = & docker @DockerArgs 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
        if ($out) { $out | ForEach-Object { Write-Information ([string]$_) -InformationAction Continue } }
        if ($code -eq 0) { return $true }
        Write-Warning "docker $($DockerArgs -join ' ') failed exit=$code (attempt $i/$Attempts); retrying..."
        Start-Sleep -Seconds (5 * $i)
    }
    return $false
}

$free = Get-HostFreeGb
Write-Host "Host free RAM: ${free} GiB (min recommended: $MinFreeGb GiB)"
if ($free -lt 2) {
    Write-Error @"
Free RAM is too low (${free} GiB). Docker Desktop will likely die immediately.
Close PyCharm heavy processes / browsers, then re-run with -RestartWsl.
"@
    exit 2
}
if ($free -lt $MinFreeGb) {
    Write-Warning @"
Free RAM is low (${free} GiB). Prefer closing IDE indexers before multi-stack work.
Continuing best-effort with main-only surface...
"@
}

if ($RestartWsl) {
    Write-Host 'Restarting WSL (reclaims vmmem; briefly interrupts Ubuntu)...'
    wsl --shutdown 2>$null
    Start-Sleep -Seconds 10
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
    Write-Error 'Docker engine did not become stable. Free RAM, then re-run with -RestartWsl.'
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

if (-not $KeepForeignContainers) {
    Stop-ForeignContainers
}

Write-Host 'Starting main stack (no rebuild, project bioetl-main)...'
$mainOk = Start-ComposeRetry -DockerArgs @(
    'compose', '-p', 'bioetl-main', '-f', 'docker-compose.yml', 'up', '-d', '--no-build'
)
if (-not $mainOk) {
    Write-Warning 'main up failed; build once only if image missing: docker compose -p bioetl-main -f docker-compose.yml build bioetl'
}

if ($WithNeo4j) {
    if (-not $env:NEO4J_PASSWORD) {
        Write-Warning 'NEO4J_PASSWORD missing; skip neo4j'
    } else {
        Write-Host 'Starting neo4j (optional helper, project bioetl-neo4j)...'
        $neoOk = Start-ComposeRetry -DockerArgs @(
            'compose', '-p', 'bioetl-neo4j', '-f', 'docker-compose.neo4j.yml', 'up', '-d'
        )
        if (-not $neoOk) {
            Write-Warning 'neo4j up failed after retries'
        }
    }
}

if ($WithMonitoring) {
    Write-Host 'Starting monitoring (opt-in)...'
    Start-ComposeRetry -DockerArgs @(
        'compose', '-p', 'bioetl-monitoring', '-f', 'docker-compose.monitoring.yml',
        'up', '-d', '--no-build'
    ) | Out-Null
} else {
    foreach ($name in @('bioetl-prometheus', 'bioetl-pushgateway', 'bioetl-grafana', 'bioetl-monitoring-renderer-1')) {
        $st = docker inspect --format '{{.State.Running}}' $name 2>$null
        if ($st -eq 'true') {
            Write-Host "Stopping leftover monitoring container $name..."
            docker stop $name 2>$null | Out-Null
        }
    }
}

Start-Sleep -Seconds 25
Write-Host '=== status ==='
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
try {
    $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/ready -TimeoutSec 5
    Write-Host "ready=$($r.StatusCode)"
} catch {
    Write-Warning "ready probe: $($_.Exception.Message)"
}
if ($WithNeo4j) {
    $neoH = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' bioetl-neo4j 2>$null
    Write-Host "neo4j=$neoH"
}

$freeAfter = Get-HostFreeGb
Write-Host "Host free RAM after start: ${freeAfter} GiB"
Write-Host @'

Stability rules (this host):
  - Always:  .\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j
  - After crash:  ... -RestartWsl -WithNeo4j
  - Never thrash compose --build / multi-stack recreate
  - Keep %USERPROFILE%\.wslconfig memory=6GB (not 16GB)
  - Keep free RAM >= 4 GiB before heavy Docker work
  - Monitoring is opt-in only
  - Auto-recover: harden-desktop-host.ps1 -RegisterWatchdog
'@

# Explicit success so callers/watchdog do not inherit a stale $LASTEXITCODE.
$mainRunning = (docker inspect --format '{{.State.Running}}' bioetl 2>$null) -eq 'true'
if (-not $mainRunning) {
    Write-Error 'bioetl container is not running after ensure-stable'
    exit 1
}
if ($WithNeo4j -and $env:NEO4J_PASSWORD) {
    $neoRunning = (docker inspect --format '{{.State.Running}}' bioetl-neo4j 2>$null) -eq 'true'
    if (-not $neoRunning) {
        Write-Warning 'bioetl-neo4j is not running (main is up)'
        exit 1
    }
}
exit 0
