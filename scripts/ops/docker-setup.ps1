# Canonical Docker setup and management entrypoint for BioETL.
#
# Retains the legacy root docker-setup.ps1 command verbs from the retired root
# helper while keeping maintained logic under scripts/ops/**.

param(
    [Parameter(Position = 0)]
    [string]$Command = "",

    [Parameter(Position = 1)]
    [string]$Service = "",

    [string]$Mode = ""
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot
$DockerPreflight = "scripts/ops/runtime/docker/docker_runtime_preflight.py"
$DockerContract = "configs/quality/docker_runtime_contracts.yaml"
$MainProject = "bioetl-main"
$MainCompose = "docker-compose.yml"
$MonitoringProject = "bioetl-monitoring"
$MonitoringCompose = "docker-compose.monitoring.yml"
$MonitoringServices = @("prometheus", "pushgateway", "renderer", "grafana")
$RestartBaseline = @{}

function Write-Info {
    Write-Host "[INFO] $args" -ForegroundColor Blue
}

function Write-Success {
    Write-Host "[SUCCESS] $args" -ForegroundColor Green
}

function Write-Warn {
    Write-Host "[WARNING] $args" -ForegroundColor Yellow
}

function Write-Fail {
    Write-Host "[ERROR] $args" -ForegroundColor Red
}

function Assert-NativeSuccess {
    param([string]$Action)
    if ($LASTEXITCODE -ne 0) { throw "$Action failed with exit code $LASTEXITCODE." }
}

function Check-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Fail "Docker is not installed. Please install Docker Desktop."
        exit 1
    }

    docker ps *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker is not running or is not accessible."
        exit 1
    }

    $docker = docker --version
    Write-Success "Docker found: $docker"
}

function Check-Compose {
    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker Compose is not available."
        exit 1
    }

    $compose = docker compose version
    Write-Success "Docker Compose found: $compose"
}

function Require-EnvFile {
    if (Test-Path ".env") {
        return
    }

    Write-Fail ".env file is missing."
    Write-Warn "Guardrail: Docker helper never creates or edits .env files."
    Write-Warn "Provide the required values through an existing approved .env or process environment, then retry."
    exit 2
}

function Get-PythonCommand {
    if ($env:BIOETL_PYTHON -and (Get-Command $env:BIOETL_PYTHON -ErrorAction SilentlyContinue)) { return $env:BIOETL_PYTHON }
    foreach ($Candidate in @("python", "python3")) { if (Get-Command $Candidate -ErrorAction SilentlyContinue) { return $Candidate } }
    throw "Python is required for the Docker runtime preflight."
}

function Invoke-RuntimePreflight {
    param([string]$Phase)
    $Python = Get-PythonCommand
    $Report = "reports/quality/docker-runtime-$Phase.json"
    Write-Info "Running fail-closed Docker runtime $Phase preflight..."
    $PreviousRepoRoot = $env:BIOETL_REPO_ROOT
    $env:BIOETL_REPO_ROOT = $ProjectRoot
    try { & $Python $DockerPreflight --contract $DockerContract --output $Report }
    finally { $env:BIOETL_REPO_ROOT = $PreviousRepoRoot }
    if ($LASTEXITCODE -ne 0) { throw "Docker runtime $Phase preflight failed. Review $Report before mutation." }
    $Payload = Get-Content -Raw $Report | ConvertFrom-Json
    foreach ($Project in @($Payload.live.compose_projects)) {
        $ProjectName = if ($Project.Name) { [string]$Project.Name } else { [string]$Project.name }
        $RawFiles = if ($Project.ConfigFiles) { $Project.ConfigFiles } else { $Project.ConfigFile }
        $ConfigFiles = if ($RawFiles -is [array]) { @($RawFiles) } else { @([string]$RawFiles -split "," | Where-Object { $_.Trim() }) }
        $NormalizedFiles = @($ConfigFiles | ForEach-Object { ([string]$_).Replace("\", "/").Trim() })
        if ($NormalizedFiles | Where-Object { $_.StartsWith("/tmp/") }) { throw "$ProjectName`: /tmp Compose config origin is forbidden." }
        if ($ProjectName.StartsWith("bioetl-") -and $NormalizedFiles.Count -ne 1) { throw "$ProjectName`: multiple owning Compose files are forbidden: $NormalizedFiles" }
    }
    Write-Success "Docker runtime $Phase preflight passed."
}

function Get-RestartKey { param([string]$Project, [string]$ServiceName); return "$Project/$ServiceName" }

function Save-RestartBaseline {
    param([string]$Project, [string]$ComposeFile, [string[]]$Services)
    foreach ($ServiceName in $Services) {
        $ContainerId = docker compose -p $Project -f $ComposeFile ps -q $ServiceName 2>$null
        $Count = 0
        if ($LASTEXITCODE -eq 0 -and $ContainerId) {
            $Count = [int](docker inspect --format '{{.RestartCount}}' $ContainerId)
            if ($LASTEXITCODE -ne 0) { throw "Could not read restart baseline for $Project/$ServiceName." }
        }
        $RestartBaseline[(Get-RestartKey -Project $Project -ServiceName $ServiceName)] = $Count
    }
}

function Assert-ServiceReady {
    param([string]$Project, [string]$ComposeFile, [string]$ServiceName)
    $ContainerId = docker compose -p $Project -f $ComposeFile ps -q $ServiceName
    if ($LASTEXITCODE -ne 0 -or -not $ContainerId) { throw "$Project/$ServiceName has no owned container." }
    $Inspection = (docker inspect $ContainerId | ConvertFrom-Json)[0]
    if ($LASTEXITCODE -ne 0 -or -not $Inspection) { throw "Could not inspect $Project/$ServiceName." }
    if ($Inspection.State.Status -ne "running" -or $Inspection.State.OOMKilled) { throw "$Project/$ServiceName failed state/OOM verification." }
    if ($Inspection.State.Health -and $Inspection.State.Health.Status -ne "healthy") { throw "$Project/$ServiceName is not healthy: $($Inspection.State.Health.Status)" }
    $Key = Get-RestartKey -Project $Project -ServiceName $ServiceName
    $Baseline = if ($RestartBaseline.ContainsKey($Key)) { [int]$RestartBaseline[$Key] } else { 0 }
    if ([int]$Inspection.RestartCount -gt $Baseline) { throw "$Project/$ServiceName restart count increased: $Baseline -> $($Inspection.RestartCount)" }
}

function Wait-BackendReadiness {
    $Deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $Deadline) {
        try {
            $Payload = Invoke-RestMethod -Uri "http://127.0.0.1:8081/ops/control-plane/ready" -TimeoutSec 2
            if ($null -ne $Payload) { return }
        }
        catch { Start-Sleep -Seconds 1 }
    }
    throw "BioETL control-plane readiness timed out."
}

function Assert-PrometheusRuntimeIdentity {
    $HostIdentity = Invoke-RestMethod -Uri "http://127.0.0.1:9090/api/v1/status/runtimeinfo" -TimeoutSec 5
    $ContainerRaw = docker compose -p $MonitoringProject -f $MonitoringCompose exec -T prometheus wget -qO- http://127.0.0.1:9090/api/v1/status/runtimeinfo
    if ($LASTEXITCODE -ne 0) { throw "Could not read container-network Prometheus runtime identity." }
    $ContainerIdentity = $ContainerRaw | ConvertFrom-Json
    if (-not $HostIdentity.data.startTime -or $HostIdentity.data.startTime -ne $ContainerIdentity.data.startTime) { throw "Host and container-network Prometheus runtime identities differ." }
    Write-Success "Prometheus runtime identity converged."
}

function Ensure-ExternalNetwork {
    param([string]$NetworkName)

    docker network inspect $NetworkName *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker network ready: $NetworkName"
        return
    }

    Write-Info "Creating shared Docker network: $NetworkName"
    docker network create $NetworkName *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Failed to create Docker network: $NetworkName"
        exit 1
    }
    Write-Success "Docker network ready: $NetworkName"
}

function Ensure-ExternalNetworks {
    Ensure-ExternalNetwork -NetworkName "bioetl-monitoring"
    Ensure-ExternalNetwork -NetworkName "warp-network"
}

function Build-Image {
    Write-Info "Building BioETL image..."
    docker build -t bioetl:latest -f Dockerfile.bioetl . `
        --build-arg BUILDKIT_INLINE_CACHE=1 `
        --progress=plain
    Write-Success "BioETL image built successfully."
}

function Start-MainStack {
    Ensure-EnvFile
    Ensure-ExternalNetworks
    Write-Info "Starting BioETL services..."
    docker compose -p bioetl-main -f docker-compose.yml up -d
    Write-Success "BioETL services started."
}

function Start-FullStack {
    Ensure-EnvFile
    Ensure-ExternalNetworks

    Write-Info "Starting Neo4j..."
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d
    Write-Success "Neo4j started."

    Write-Info "Starting Redis..."
    docker compose -p bioetl-redis -f scripts/ops/runtime/docker/compose/redis.yml up -d
    Write-Success "Redis started."

    Write-Info "Starting MinIO..."
    docker compose -p bioetl-minio -f scripts/ops/runtime/docker/compose/minio.yml up -d
    Write-Success "MinIO started."

    Write-Info "Starting monitoring stack..."
    docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml up -d
    Write-Success "Monitoring stack started."

    Write-Info "Starting BioETL services..."
    docker compose -p bioetl-main -f docker-compose.yml up -d
    Write-Success "BioETL services started."
}

function Start-Monitoring {
    Ensure-EnvFile
    Ensure-ExternalNetworks
    Write-Info "Starting monitoring stack..."
    docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml up -d
    Write-Success "Monitoring stack started."
}

function Start-MCP {
    Ensure-EnvFile
    Ensure-ExternalNetworks
    Write-Info "Starting MCP servers..."
    docker compose -p bioetl-codex -f docker-compose.codex.yml up -d
    Write-Success "MCP servers started."
}

function Stop-MainStack {
    Write-Info "Stopping BioETL services..."
    docker compose -p bioetl-main -f docker-compose.yml down
    Write-Success "BioETL services stopped."
}

function Stop-FullStack {
    Write-Info "Stopping all Docker helper services..."
    docker compose -p bioetl-main -f docker-compose.yml down
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml down 2>$null
    docker compose -p bioetl-redis -f scripts/ops/runtime/docker/compose/redis.yml down 2>$null
    docker compose -p bioetl-minio -f scripts/ops/runtime/docker/compose/minio.yml down 2>$null
    docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml down 2>$null
    docker compose -p bioetl-codex -f docker-compose.codex.yml down 2>$null
    Write-Success "All Docker helper services stopped."
}

function View-Logs {
    param([string]$TargetService = "")

    if ($TargetService -eq "") {
        docker compose -p bioetl-main -f docker-compose.yml logs -f
    }
    else {
        docker compose -p bioetl-main -f docker-compose.yml logs -f $TargetService
    }
}

function Health-Check {
    Write-Info "Checking service health..."
    docker compose -p bioetl-main -f docker-compose.yml ps

    docker compose -p bioetl-main -f docker-compose.yml exec -T bioetl curl -f http://127.0.0.1:8081/health/ready 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "BioETL is healthy."
    }
    else {
        Write-Warn "BioETL health check failed."
    }
}

function Cleanup {
    Write-Warn "Removing Docker resources for the main BioETL stack."
    docker compose -p bioetl-main -f docker-compose.yml down --volumes
    docker rmi bioetl:latest 2>$null
    Write-Success "Cleanup complete."
}

function Show-Usage {
    @"
BioETL Docker Management Script (Windows PowerShell)

Usage: .\scripts\ops\docker-setup.ps1 <command> [options]

Commands:
    check          Check Docker and Docker Compose availability
    build          Build bioetl:latest from Dockerfile.bioetl
    start          Start main services and check health
    start-full     Build the image, start full helper stack, and check health
    stop           Stop main services
    stop-full      Stop main plus helper compose stacks
    logs [service] View logs, optionally for a specific service
    health         Check service health
    clean          Remove main stack volumes and bioetl:latest image
    help           Show this help message

Mode compatibility:
    -Mode basic       Alias for start
    -Mode full        Alias for start-full
    -Mode monitoring  Start monitoring stack only
    -Mode mcp         Start Codex MCP stack only

Examples:
    .\scripts\ops\docker-setup.ps1 check
    .\scripts\ops\docker-setup.ps1 build
    .\scripts\ops\docker-setup.ps1 start-full
    .\scripts\ops\docker-setup.ps1 logs bioetl
    .\scripts\ops\docker-setup.ps1 stop-full
"@
}

function Invoke-CommandMode {
    param([string]$SelectedCommand)

    switch ($SelectedCommand) {
        "check" {
            Check-Docker
            Check-Compose
        }
        "build" {
            Check-Docker
            Build-Image
        }
        "start" {
            Check-Docker
            Start-MainStack
            Start-Sleep -Seconds 2
            Health-Check
        }
        "start-full" {
            Check-Docker
            Build-Image
            Start-FullStack
            Start-Sleep -Seconds 5
            Health-Check
        }
        "basic" {
            Check-Docker
            Start-MainStack
            Start-Sleep -Seconds 2
            Health-Check
        }
        "full" {
            Check-Docker
            Build-Image
            Start-FullStack
            Start-Sleep -Seconds 5
            Health-Check
        }
        "monitoring" {
            Check-Docker
            Start-Monitoring
        }
        "mcp" {
            Check-Docker
            Start-MCP
        }
        "stop" {
            Check-Docker
            Stop-MainStack
        }
        "stop-full" {
            Check-Docker
            Stop-FullStack
        }
        "logs" {
            Check-Docker
            View-Logs -TargetService $Service
        }
        "health" {
            Check-Docker
            Health-Check
        }
        "clean" {
            Check-Docker
            Cleanup
        }
        "help" {
            Show-Usage
        }
        "" {
            Show-Usage
        }
        default {
            Write-Fail "Unknown command: $SelectedCommand"
            Show-Usage
            exit 1
        }
    }
}

if ($Command -eq "" -and $Mode -ne "") {
    Invoke-CommandMode -SelectedCommand $Mode
}
elseif ($Command -ne "") {
    Invoke-CommandMode -SelectedCommand $Command
}
else {
    Show-Usage
}
