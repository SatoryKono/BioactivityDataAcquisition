#!/usr/bin/env pwsh
# Helper: Check Gemini environment
# Called by: run-gemini.ps1

param(
    [switch]$SkipSetup = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$HelperDir = Join-Path $ScriptDir "helper"

# Colors
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
}

function Log-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Log-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Log-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Log-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Gemini Environment Check" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$AllChecks = $true

# 1. Check WSL
Log-Info "Checking WSL..."
try {
    $wslTest = wsl --list 2>$null
    if ($?) {
        Log-Success "WSL is available"
    } else {
        Log-Error "WSL not responding"
        $AllChecks = $false
    }
} catch {
    Log-Error "WSL not found"
    $AllChecks = $false
}

# 2. Check API Key in .env.gemini
Log-Info "Checking API key..."
$EnvFile = Join-Path $RootDir ".env.gemini"
if (Test-Path $EnvFile) {
    $Content = Get-Content $EnvFile
    if ($Content -match "GEMINI_API_KEY=" -and $Content -notmatch "GEMINI_API_KEY=your-api-key-here") {
        Log-Success "API key found in .env.gemini"
    } else {
        Log-Warn ".env.gemini exists but API key missing"
        $AllChecks = $false
    }
} else {
    Log-Warn ".env.gemini not found"
    $AllChecks = $false
}

# 3. Check Python in WSL
Log-Info "Checking Python..."
$pythonCheck = wsl -- python3 --version 2>$null
if ($?) {
    Log-Success "Python is installed: $(wsl -- python3 --version)"
} else {
    Log-Warn "Python3 not found in WSL"
    $AllChecks = $false
    if (-not $SkipSetup) {
        Log-Info "Will install Python automatically"
    }
}

# 4. Check pip
Log-Info "Checking pip..."
$pipCheck = wsl -- pip3 --version 2>$null
if ($?) {
    Log-Success "pip3 is installed"
} else {
    Log-Warn "pip3 not found"
    $AllChecks = $false
    if (-not $SkipSetup) {
        Log-Info "Will install pip automatically"
    }
}

# 5. Check Gemini SDK package
Log-Info "Checking Gemini Python SDK..."
$pkgCheck = wsl -- bash -lc 'compgen -G "$HOME/.cache/tools/gemini-venv/lib/python*/site-packages/google/genai" >/dev/null || compgen -G "$HOME/.cache/tools/gemini-venv/lib/python*/site-packages/google/generativeai" >/dev/null' 2>$null
if ($?) {
    $newSdkCheck = wsl -- bash -lc 'compgen -G "$HOME/.cache/tools/gemini-venv/lib/python*/site-packages/google/genai" >/dev/null' 2>$null
    if ($?) {
        Log-Success "Google GenAI SDK is installed"
    } else {
        Log-Warn "Legacy google-generativeai package is installed; rerun setup to migrate"
    }
} else {
    Log-Warn "Gemini Python SDK not installed"
    $AllChecks = $false
    if (-not $SkipSetup) {
        Log-Info "Will install package automatically"
    }
}

# 6. Create .env.gemini if missing
if (-not (Test-Path $EnvFile)) {
    Log-Warn "Creating .env.gemini template..."
    @"
# Google Gemini Configuration
# Get your API key from: https://aistudio.google.com/app/apikeys
GEMINI_API_KEY=your-api-key-here
"@ | Set-Content $EnvFile
    Log-Success ".env.gemini created - please edit and add your API key"
}

Write-Host ""

# Return status
@{
    AllChecks = $AllChecks
    RootDir = $RootDir
    HelperDir = $HelperDir
    EnvFile = $EnvFile
}
