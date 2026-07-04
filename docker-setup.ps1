# BioETL Docker setup and management script for Windows PowerShell

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    
    [Parameter(Position = 1)]
    [string]$Service = ""
)

# Helper functions
function Write-Info {
    Write-Host "[INFO] $args" -ForegroundColor Blue
}

function Write-Success {
    Write-Host "[SUCCESS] $args" -ForegroundColor Green
}

function Write-Warning {
    Write-Host "[WARNING] $args" -ForegroundColor Yellow
}

function Write-Error {
    Write-Host "[ERROR] $args" -ForegroundColor Red
}

# Check Docker installation
function Check-Docker {
    try {
        $docker = docker --version
        Write-Success "Docker found: $docker"
    }
    catch {
        Write-Error "Docker is not installed. Please install Docker Desktop."
        exit 1
    }
}

# Check Docker Compose
function Check-Compose {
    try {
        $compose = docker compose version
        Write-Success "Docker Compose found: $compose"
    }
    catch {
        Write-Error "Docker Compose is not available."
        exit 1
    }
}

# Build BioETL image
function Build-Image {
    Write-Info "Building BioETL image..."
    docker build -t bioetl:latest -f Dockerfile.bioetl . `
        --build-arg BUILDKIT_INLINE_CACHE=1 `
        --progress=plain
    Write-Success "BioETL image built successfully"
}

# Start services
function Start-Services {
    param([string]$Mode = "basic")
    
    Write-Info "Starting Docker services..."
    
    if ($Mode -eq "full" -or $Mode -eq "all") {
        Write-Info "Starting Neo4j..."
        docker compose -f docker-compose.neo4j.yml up -d
        Write-Success "Neo4j started"
        
        Write-Info "Starting Redis..."
        docker compose -f scripts/ops/runtime/docker/compose/redis.yml up -d
        Write-Success "Redis started"
        
        Write-Info "Starting MinIO..."
        docker compose -f scripts/ops/runtime/docker/compose/minio.yml up -d
        Write-Success "MinIO started"
        
        Write-Info "Starting monitoring stack..."
        docker compose -f docker-compose.monitoring.yml up -d
        Write-Success "Monitoring stack started"
    }
    
    Write-Info "Starting BioETL services..."
    docker compose up -d
    Write-Success "BioETL services started"
}

# Stop services
function Stop-Services {
    param([string]$Mode = "basic")
    
    Write-Info "Stopping services..."
    docker compose down
    
    if ($Mode -eq "full" -or $Mode -eq "all") {
        docker compose -f docker-compose.neo4j.yml down 2>$null
        docker compose -f scripts/ops/runtime/docker/compose/redis.yml down 2>$null
        docker compose -f scripts/ops/runtime/docker/compose/minio.yml down 2>$null
        docker compose -f docker-compose.monitoring.yml down 2>$null
    }
    
    Write-Success "Services stopped"
}

# View logs
function View-Logs {
    param([string]$Service = "")
    
    if ($Service -eq "") {
        docker compose logs -f
    }
    else {
        docker compose logs -f $Service
    }
}

# Health check
function Health-Check {
    Write-Info "Checking service health..."
    
    docker compose ps
    
    try {
        $health = docker compose exec -T bioetl curl -f http://127.0.0.1:8081/health/ready 2>$null
        Write-Success "BioETL is healthy"
    }
    catch {
        Write-Warning "BioETL health check failed"
    }
}

# Clean up
function Cleanup {
    Write-Warning "Removing Docker resources..."
    docker compose down --volumes
    docker rmi bioetl:latest 2>$null
    Write-Success "Cleanup complete"
}

# Usage
function Show-Usage {
    @"
BioETL Docker Management Script (Windows PowerShell)

Usage: .\docker-setup.ps1 <command> [options]

Commands:
    check          Check Docker installation
    build          Build BioETL image
    start          Start main services
    start-full     Start all services (including Neo4j, Redis, monitoring)
    stop           Stop main services
    stop-full      Stop all services
    logs [service] View logs (optionally for specific service)
    health         Check service health
    clean          Remove all Docker resources
    help           Show this help message

Examples:
    .\docker-setup.ps1 check
    .\docker-setup.ps1 build
    .\docker-setup.ps1 start-full
    .\docker-setup.ps1 logs bioetl
    .\docker-setup.ps1 stop-full

"@
}

# Main logic
switch ($Command) {
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
        Start-Services "basic"
        Start-Sleep -Seconds 2
        Health-Check
    }
    "start-full" {
        Check-Docker
        Build-Image
        Start-Services "full"
        Start-Sleep -Seconds 5
        Health-Check
    }
    "stop" {
        Check-Docker
        Stop-Services "basic"
    }
    "stop-full" {
        Check-Docker
        Stop-Services "full"
    }
    "logs" {
        Check-Docker
        View-Logs $Service
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
    default {
        Write-Error "Unknown command: $Command"
        Show-Usage
        exit 1
    }
}
