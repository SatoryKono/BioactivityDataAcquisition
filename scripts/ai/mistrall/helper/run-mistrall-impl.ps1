#!/usr/bin/env pwsh
# Helper: Run Mistral operations on Windows
# Called by: run-mistrall.ps1

param(
    [string]$Command = "start",
    [string[]]$Args = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

# Load environment
$envFile = Join-Path $RootDir ".env.mistrall"
$env:MISTRALL_PORT = "11434"
$env:MISTRALL_MODEL = "mistral:latest"
$env:OLLAMA_CONTAINER = "mistral-ollama"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $varName = $matches[1]
            $varValue = $matches[2]
            [System.Environment]::SetEnvironmentVariable($varName, $varValue)
            Set-Variable -Name $varName -Value $varValue -Scope Script
        }
    }
}

$composeFile = Join-Path $RootDir "docker-compose.mistrall.yml"

# Function: Start service
function Start-Service {
    Write-Info "Starting Mistral Ollama service..."
    Write-Host ""

    Push-Location $RootDir
    docker compose -f $composeFile up
    Pop-Location
}

# Function: Start daemon
function Start-Daemon {
    Write-Info "Starting Mistral as daemon..."

    Push-Location $RootDir
    docker compose -f $composeFile up -d
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -eq 0) {
        Write-Success "Mistral daemon started (container: $env:OLLAMA_CONTAINER)"
        Write-Info "API: http://localhost:$env:MISTRALL_PORT"
        Write-Info "View logs: .\run-mistrall.ps1 logs"
    }

    return $exitCode
}

# Function: Stop service
function Stop-Service {
    Write-Info "Stopping Mistral..."

    Push-Location $RootDir
    docker compose -f $composeFile down
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -eq 0) {
        Write-Success "Mistral stopped"
    }

    return $exitCode
}

# Function: Show status
function Show-Status {
    Write-Info "Checking Mistral status..."
    Write-Host ""

    $running = docker ps --filter "name=$env:OLLAMA_CONTAINER" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}" 2>$null

    if ($running) {
        Write-Success "Mistral is RUNNING"
        Write-Host $running
        Write-Info "API: http://localhost:$env:MISTRALL_PORT"
    } else {
        Write-Warn "Mistral is not running"
        Write-Info "Start with: .\run-mistrall.ps1 daemon"
    }
}

# Function: Show logs
function Show-Logs {
    Write-Info "Showing Mistral logs..."
    Write-Host ""

    Push-Location $RootDir
    docker compose -f $composeFile logs -f
    Pop-Location
}

# Function: Shell access
function Shell-Access {
    Write-Info "Opening shell in Mistral container..."

    $containerId = docker ps -q -f "name=$env:OLLAMA_CONTAINER" 2>$null | Select-Object -First 1

    if (-not $containerId) {
        Write-Error "Mistral container not running"
        return 1
    }

    docker exec -it $containerId bash 2>$null
}

# Function: Pull model
function Pull-Model {
    Write-Info "Pulling model: $env:MISTRALL_MODEL"

    $containerId = docker ps -q -f "name=$env:OLLAMA_CONTAINER" 2>$null | Select-Object -First 1

    if (-not $containerId) {
        Write-Error "Mistral container not running"
        Write-Info "Start it first: .\run-mistrall.ps1 daemon"
        return 1
    }

    docker exec -it $containerId ollama pull $env:MISTRALL_MODEL
    return $LASTEXITCODE
}

# Main dispatcher
switch ($Command) {
    "start" { Start-Service }
    "daemon" { Start-Daemon }
    "stop" { Stop-Service }
    "status" { Show-Status }
    "logs" { Show-Logs }
    "shell" { Shell-Access }
    "pull" { Pull-Model }
    default {
        Write-Error "Unknown operation: $Command"
        exit 1
    }
}

exit $LASTEXITCODE
