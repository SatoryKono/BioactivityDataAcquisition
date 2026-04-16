#!/usr/bin/env pwsh
# Helper: Check Mistral environment on Windows
# Called by: run-mistrall.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mistral Environment Check (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$allChecks = $true

# 1. Check Docker
Write-Info "Checking Docker..."
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker installed: $dockerVersion"
    } else {
        Write-Warn "Docker not found"
        $allChecks = $false
    }
} catch {
    Write-Warn "Docker not accessible"
    $allChecks = $false
}

# 2. Check Docker daemon
Write-Info "Checking Docker daemon..."
try {
    $dockerPs = docker ps 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker daemon running"
    } else {
        Write-Warn "Docker daemon not accessible - may need to start Docker Desktop"
        $allChecks = $false
    }
} catch {
    Write-Warn "Docker daemon not accessible"
    $allChecks = $false
}

# 3. Check Docker Compose
Write-Info "Checking Docker Compose..."
try {
    $composeVersion = docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker Compose available: $composeVersion"
    } else {
        Write-Warn "Docker Compose not available"
        $allChecks = $false
    }
} catch {
    Write-Warn "Docker Compose not available"
    $allChecks = $false
}

# 4. Check .env.mistrall
Write-Info "Checking configuration..."
$envFile = Join-Path $RootDir ".env.mistrall"
if (Test-Path $envFile) {
    Write-Success ".env.mistrall exists"
} else {
    Write-Warn ".env.mistrall not found"
    $allChecks = $false
}

# 5. Check docker-compose.mistrall.yml
Write-Info "Checking docker-compose.mistrall.yml..."
$composeFile = Join-Path $RootDir "docker-compose.mistrall.yml"
if (Test-Path $composeFile) {
    Write-Success "docker-compose.mistrall.yml exists"
} else {
    Write-Warn "docker-compose.mistrall.yml not found"
    $allChecks = $false
}

Write-Host ""

if ($allChecks) {
    Write-Success "All checks passed"
    exit 0
} else {
    Write-Warn "Some checks failed"
    exit 1
}
