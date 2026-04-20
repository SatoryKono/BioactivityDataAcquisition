#!/usr/bin/env pwsh
# Helper: Check Mistral Vibe environment on Windows
# Called by: run-vibe.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mistral Vibe Environment Check (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$allChecks = $true

# 1. Check Node.js
Write-Info "Checking Node.js..."
try {
    $nodeVersion = node --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Node.js installed: $nodeVersion"
    } else {
        Write-Warn "Node.js not found"
        $allChecks = $false
    }
} catch {
    Write-Warn "Node.js not found"
    $allChecks = $false
}

# 2. Check npm
Write-Info "Checking npm..."
try {
    $npmVersion = npm --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "npm installed: $npmVersion"
    } else {
        Write-Warn "npm not found"
        $allChecks = $false
    }
} catch {
    Write-Warn "npm not found"
    $allChecks = $false
}

# 3. Check .env.mistrallvibe
Write-Info "Checking configuration..."
$envFile = Join-Path $RootDir ".env.mistrallvibe"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "VIBE_API_KEY=") {
        if ($envContent -match "your-api-key-here") {
            Write-Warn ".env.mistrallvibe exists but VIBE_API_KEY not configured"
            $allChecks = $false
        } else {
            Write-Success ".env.mistrallvibe configured with API key"
        }
    } else {
        Write-Warn ".env.mistrallvibe missing VIBE_API_KEY"
        $allChecks = $false
    }
} else {
    Write-Warn ".env.mistrallvibe not found"
    $allChecks = $false
}

# 4. Check if Vibe is installed
Write-Info "Checking Mistral Vibe installation..."
try {
    $vibeVersion = vibe --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Mistral Vibe installed: $vibeVersion"
    } else {
        Write-Warn "Mistral Vibe not found"
        $allChecks = $false
    }
} catch {
    Write-Warn "Mistral Vibe not found in PATH"
    $allChecks = $false
}

Write-Host ""

if ($allChecks) {
    Write-Success "All checks passed"
    exit 0
} else {
    Write-Warn "Some checks failed - run setup first"
    exit 1
}
