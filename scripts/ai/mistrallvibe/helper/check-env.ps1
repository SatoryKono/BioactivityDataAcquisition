#!/usr/bin/env pwsh
# Helper: Check Mistral Vibe environment on Windows with timeouts
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

# 1. Check Node.js (with timeout)
Write-Info "Checking Node.js..."
try {
    $nodeJob = Start-Job -ScriptBlock { node --version }
    $nodeResult = Wait-Job -Job $nodeJob -Timeout 5 | Receive-Job
    Remove-Job -Job $nodeJob -Force 2>$null
    
    if ($nodeResult) {
        Write-Success "Node.js installed: $nodeResult"
    } else {
        Write-Warn "Node.js not found or timed out"
        $allChecks = $false
    }
} catch {
    Write-Warn "Node.js not found"
    $allChecks = $false
}

# 2. Check npm (with timeout)
Write-Info "Checking npm..."
try {
    $npmJob = Start-Job -ScriptBlock { npm --version }
    $npmResult = Wait-Job -Job $npmJob -Timeout 5 | Receive-Job
    Remove-Job -Job $npmJob -Force 2>$null
    
    if ($npmResult) {
        Write-Success "npm installed: $npmResult"
    } else {
        Write-Warn "npm not found or timed out"
        $allChecks = $false
    }
} catch {
    Write-Warn "npm not found"
    $allChecks = $false
}

# 3. Check Python (with timeout)
Write-Info "Checking Python..."
try {
    $pythonJob = Start-Job -ScriptBlock { python3 --version }
    $pythonResult = Wait-Job -Job $pythonJob -Timeout 5 | Receive-Job
    Remove-Job -Job $pythonJob -Force 2>$null
    
    if ($pythonResult) {
        Write-Success "Python installed: $pythonResult"
    } else {
        Write-Warn "Python not found or timed out"
        $allChecks = $false
    }
} catch {
    Write-Warn "Python not found"
    $allChecks = $false
}

# 4. Check .env.mistrallvibe
Write-Info "Checking configuration..."
$envFile = Join-Path $RootDir ".env.mistrallvibe"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "MISTRAL_API_KEY=" -or $envContent -match "VIBE_API_KEY=") {
        if ($envContent -match "your-api-key-here") {
            Write-Warn ".env.mistrallvibe exists but API key not configured"
            $allChecks = $false
        } else {
            Write-Success ".env.mistrallvibe configured with API key"
        }
    } else {
        Write-Warn ".env.mistrallvibe missing MISTRAL_API_KEY"
        $allChecks = $false
    }
} else {
    Write-Warn ".env.mistrallvibe not found"
    $allChecks = $false
}

# 5. Check if Vibe is installed (with timeout)
Write-Info "Checking Mistral Vibe installation..."
try {
    $vibeJob = Start-Job -ScriptBlock { vibe --version 2>$null }
    $vibeResult = Wait-Job -Job $vibeJob -Timeout 5 | Receive-Job
    Remove-Job -Job $vibeJob -Force 2>$null
    
    if ($vibeResult) {
        Write-Success "Mistral Vibe installed: $vibeResult"
    } else {
        Write-Warn "Mistral Vibe not found in PATH"
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
