# Canonical Docker setup and management entrypoint for BioETL.
#
# Retains the legacy root docker-setup.ps1 command verbs from the retired root
# helper while keeping maintained logic under scripts/ops/**.

param(
    [Parameter(Position = 0)]
    [string]$Command = "",

    [Parameter(Position = 1)]
    [string]$Service = "",

    [string]$Mode = "",

    [switch]$AllowEnvFileCreate
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

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

function Ensure-EnvFile {
    if (Test-Path ".env") {
        return
    }

    if ($AllowEnvFileCreate -or $env:BIOETL_CREATE_LOCAL_ENV_FILES -eq "1") {
        if (-not (Test-Path ".env.example")) {
            Write-Fail ".env.example not found; .env was not created."
            exit 2
        }

        Write-Warn ".env file is missing; BIOETL_CREATE_LOCAL_ENV_FILES=1 or explicit opt-in allows creating it from the example."
        Copy-Item ".env.example" ".env"
        Write-Success "Created .env file. Edit it before using secrets."
        return
    }

    Write-Fail ".env file is missing."
    Write-Warn "Guardrail: Docker helper не создает .env автоматически."
    Write-Warn "Create it manually after an explicit local decision: Copy-Item .env.example .env"
    Write-Warn "Rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 only when local .env creation is intended."
    Write-Warn "Default behavior is non-mutating without BIOETL_CREATE_LOCAL_ENV_FILES=1."
    exit 2
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
