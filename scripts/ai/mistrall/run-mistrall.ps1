#!/usr/bin/env pwsh
# Mistral - Main Entry Point (Windows)
# Usage: .\run-mistrall.ps1 [command] [args]

param(
    [string]$Command = "start",
    [string[]]$Args = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperDir = Join-Path $ScriptDir "helper"
$RepoRoot = $PSScriptRoot

# Colors
$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mistral - AI Model Server (via Ollama)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Show help
if ($Command -eq "help" -or $Command -eq "-h" -or $Command -eq "--help") {
    Write-Host "Usage: .\run-mistrall.ps1 [command] [args]" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  (no args)      Start Mistral in interactive mode"
    Write-Host "  start          Start Mistral service in foreground"
    Write-Host "  daemon         Start Mistral as background service"
    Write-Host "  stop           Stop running Mistral service"
    Write-Host "  status         Check if Mistral is running"
    Write-Host "  logs           View Mistral service logs"
    Write-Host "  shell          Access Mistral container shell"
    Write-Host "  check          Check environment setup"
    Write-Host "  setup          Setup missing components (Docker, Ollama)"
    Write-Host "  pull           Pull latest Mistral model"
    Write-Host "  help           Show this help"
    Write-Host ""
    Write-Host "Environment:" -ForegroundColor Green
    Write-Host "  MISTRALL_PORT      Service port (default: 11434)"
    Write-Host "  MISTRALL_MODEL     Model name (default: mistral:latest)"
    Write-Host "  MISTRALL_MEMORY    Memory allocation (default: 2g)"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\run-mistrall.ps1"
    Write-Host "  .\run-mistrall.ps1 start"
    Write-Host "  .\run-mistrall.ps1 daemon"
    Write-Host "  .\run-mistrall.ps1 logs"
    Write-Host ""
    exit 0
}

# Process administrative commands before launch preflight.
switch -Regex ($Command) {
    "^check$" {
        & "$HelperDir\check-env.ps1"
        exit $LASTEXITCODE
    }
    "^setup$" {
        Write-Warn "Setup on Windows requires Docker Desktop"
        Write-Info "Please ensure Docker Desktop is installed and running"
        Write-Host ""
        & "$HelperDir\check-env.ps1"
        exit $LASTEXITCODE
    }
}

# Check Docker
Write-Info "Checking Docker installation..."
$dockerExists = $false
try {
    $dockerCheck = docker --version 2>$null
    $dockerExists = $LASTEXITCODE -eq 0
} catch {
    $dockerExists = $false
}

if ($dockerExists) {
    Write-Success "Docker found: $dockerCheck"
} else {
    Write-Warn "Docker not found"
}

Write-Host ""

if (-not $dockerExists) {
    if ($Command -ne "setup") {
        Write-Warn "Docker is required"
        Write-Info "Run setup first: .\run-mistrall.ps1 setup"
        Write-Host ""
        exit 1
    }
}

# Process command
switch -Regex ($Command) {
    "^help|^-h|^--help$" {
        exit 0
    }
    
    "^start$|^$" {
        Write-Info "Starting Mistral in foreground..."
        Write-Host ""
        & "$HelperDir\run-mistrall-impl.ps1" start @Args
    }
    
    "^daemon$" {
        Write-Info "Starting Mistral as daemon..."
        Write-Host ""
        & "$HelperDir\run-mistrall-impl.ps1" daemon @Args
    }
    
    "^stop$" {
        Write-Info "Stopping Mistral..."
        & "$HelperDir\run-mistrall-impl.ps1" stop @Args
    }
    
    "^status$" {
        Write-Info "Checking Mistral status..."
        & "$HelperDir\run-mistrall-impl.ps1" status @Args
    }
    
    "^logs$" {
        Write-Info "Viewing Mistral logs..."
        & "$HelperDir\run-mistrall-impl.ps1" logs @Args
    }
    
    "^shell$" {
        Write-Info "Opening Mistral container shell..."
        Write-Host ""
        & "$HelperDir\run-mistrall-impl.ps1" shell @Args
    }
    
    "^pull$" {
        Write-Info "Pulling latest Mistral model..."
        Write-Host ""
        & "$HelperDir\run-mistrall-impl.ps1" pull @Args
    }
    
    default {
        Write-Error "Unknown command: $Command"
        Write-Info "Use '.\run-mistrall.ps1 help' for usage"
        exit 1
    }
}

exit $LASTEXITCODE
