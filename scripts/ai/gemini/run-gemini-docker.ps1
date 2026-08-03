#!/usr/bin/env pwsh
# Gemini - Docker Entry Point
# Usage: .\run-gemini-docker.ps1 [command] [prompt]

param(
    [string]$Command = "start",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\.."))
$ComposeFile = Join-Path $RepoRoot "docker-compose.gemini.yml"
$EnvFile = Join-Path $ScriptDir ".env.gemini"
$CanCreateEnvFile = $env:BIOETL_CREATE_LOCAL_ENV_FILES -eq "1"

# Colors
function Write-Success { param([string]$msg); Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg); Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-ErrorMessage { param([string]$msg); Write-Host "[X] $msg" -ForegroundColor Red }
function Write-Info { param([string]$msg); Write-Host "[i] $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "=================================================="
Write-Host "  Gemini - Docker Mode"
Write-Host "=================================================="
Write-Host ""

# Check Docker
Write-Info "Checking Docker..."
try {
    $null = docker --version 2>&1
    Write-Success "Docker is available"
} catch {
    Write-ErrorMessage "Docker not found. Please install Docker Desktop."
    exit 1
}

# Check Docker is running
try {
    $null = docker ps 2>&1
} catch {
    Write-ErrorMessage "Docker is not running. Please start Docker Desktop."
    exit 1
}

# Check API key
Write-Info "Checking API key..."
if (-not (Test-Path $EnvFile)) {
    if (-not $CanCreateEnvFile) {
        Write-ErrorMessage ".env.gemini not found. Create it manually, or rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 to generate a local template."
        exit 1
    }

    Write-Warn "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.gemini template..."
    @(
        "# Google Gemini CLI Configuration",
        "# Get your API key from: https://aistudio.google.com/app/apikeys",
        "GEMINI_API_KEY=your-api-key-here",
        "# Optional model override",
        "# GEMINI_MODEL=gemini-2.5-flash"
    ) | Out-File -FilePath $EnvFile -Encoding UTF8
    Write-ErrorMessage "Please edit $EnvFile and add your Gemini API key"
    exit 1
}

# Load API key from env file
$envContent = Get-Content $EnvFile | Where-Object { $_ -match '^GEMINI_API_KEY=' }
if ($envContent -match 'GEMINI_API_KEY=(.+)') {
    $apiKey = $matches[1].Trim()
    if ($apiKey -eq "your-api-key-here" -or [string]::IsNullOrWhiteSpace($apiKey)) {
        Write-ErrorMessage "Please set GEMINI_API_KEY in $EnvFile"
        exit 1
    }
    $env:GEMINI_API_KEY = $apiKey
    Write-Success "API key loaded"
} else {
    Write-ErrorMessage "GEMINI_API_KEY not found in $EnvFile"
    exit 1
}

# Build image if needed
Write-Info "Checking Docker image..."
$imageExists = docker images -q bioetl-gemini:latest
if ([string]::IsNullOrWhiteSpace($imageExists)) {
    Write-Info "Building Docker image (this may take a few minutes)..."
    Write-Warn "DO NOT CLOSE THIS WINDOW"
    Write-Host ""
    Push-Location $RepoRoot
    try {
        docker-compose -f $ComposeFile build
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMessage "Docker build failed"
            exit 1
        }
        Write-Success "Docker image built successfully"
    } finally {
        Pop-Location
    }
} else {
    Write-Success "Docker image exists"
}

Write-Host ""

# Process command
Push-Location $RepoRoot
try {
    switch ($Command) {
        "check" {
            Write-Success "Docker environment is ready"
            Write-Info "Run: .\scripts\ai\gemini\run-gemini-docker.ps1"
        }
        "build" {
            Write-Info "Rebuilding Docker image..."
            docker-compose -f $ComposeFile build --no-cache
        }
        "start" {
            if ($Prompt.Count -gt 0) {
                $promptText = $Prompt -join " "
                Write-Info "Launching Gemini with prompt..."
                docker-compose -f $ComposeFile run --rm gemini $promptText
            } else {
                Write-Info "Launching Gemini in interactive mode..."
                Write-Info "Press Ctrl+C to exit"
                Write-Host ""
                docker-compose -f $ComposeFile run --rm gemini
            }
        }
        "exec" {
            if ($Prompt.Count -eq 0) {
                Write-ErrorMessage "exec mode requires a prompt"
                exit 1
            }
            $promptText = $Prompt -join " "
            Write-Info "Launching Gemini in auto-execute mode..."
            docker-compose -f $ComposeFile run --rm gemini --approval-mode yolo $promptText
        }
        "shell" {
            Write-Info "Launching shell in container..."
            docker-compose -f $ComposeFile run --rm gemini /bin/sh
        }
        "clean" {
            Write-Info "Stopping and removing containers..."
            docker-compose -f $ComposeFile down
            Write-Info "Removing Docker image..."
            docker rmi bioetl-gemini:latest
            Write-Success "Cleanup complete"
        }
        default {
            # Treat as prompt
            $promptText = if ($Prompt.Count -gt 0) { $Prompt -join " " } else { $Command }
            Write-Info "Launching Gemini with prompt..."
            docker-compose -f $ComposeFile run --rm gemini $promptText
        }
    }
} finally {
    Pop-Location
}

exit $LASTEXITCODE
