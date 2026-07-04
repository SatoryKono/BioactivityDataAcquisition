#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Configure the Gemini WSL launcher and managed runtime.

.DESCRIPTION
    Checks WSL availability, runs the canonical Gemini setup inside WSL, and
    reports the API-key configuration state. This script does not create or edit
    .env.gemini unless the delegated Bash setup is explicitly run with
    BIOETL_CREATE_LOCAL_ENV_FILES=1.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

function Write-Header {
    param([string]$Message)
    Write-Host "========================================================================" -ForegroundColor Green
    Write-Host "  $Message" -ForegroundColor Green
    Write-Host "========================================================================"
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n>> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning-Message {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

Write-Header "Starting Gemini WSL Setup"

Write-Step "Step 1: Checking WSL availability"
$wslExe = Get-GeminiWslCommand
if (-not $wslExe) {
    Write-Error-Message "wsl.exe was not found from this PowerShell session."
    Write-Host "Install WSL 2, restore C:\Windows\System32 in PATH, or verify with: where.exe wsl"
    exit 1
}

$wslArgs = @()
$wslArgs += Get-GeminiWslDistroArgs
$wslArgs += @("--", "true")
& $wslExe @wslArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "WSL is installed, but the selected distro is not usable."
    if ($env:BIOETL_WSL_DISTRO) {
        Write-Host "BIOETL_WSL_DISTRO=$($env:BIOETL_WSL_DISTRO)"
    }
    exit $LASTEXITCODE
}
Write-Success "WSL is available."

Write-Step "Step 2: Checking Gemini API-key file"
$envGeminiPath = Join-Path $ScriptDir ".env.gemini"
if (-not (Test-Path -LiteralPath $envGeminiPath)) {
    Write-Warning-Message ".env.gemini not found; setup will not create it by default."
    Write-Host "Create scripts\ai\gemini\.env.gemini manually with GEMINI_API_KEY before launching Gemini."
    Write-Host "To generate a local template explicitly, rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1."
}
else {
    $envContent = Get-Content -LiteralPath $envGeminiPath -Raw
    if ($envContent -match 'GEMINI_API_KEY="?[^"#\s]+' -and $envContent -notmatch 'GEMINI_API_KEY=your-api-key-here') {
        Write-Success ".env.gemini contains a non-placeholder GEMINI_API_KEY entry."
    }
    else {
        Write-Warning-Message ".env.gemini exists, but GEMINI_API_KEY is missing or still a placeholder."
    }
}

Write-Step "Step 3: Running Gemini setup in WSL"
$setupBatPath = Join-Path $ScriptDir "setup-gemini-wsl.bat"
if (-not (Test-Path -LiteralPath $setupBatPath)) {
    Write-Error-Message "Script setup-gemini-wsl.bat not found: $setupBatPath"
    exit 1
}

& cmd.exe /c "`"$setupBatPath`" /noninteractive"
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "Gemini WSL setup failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

Write-Header "Gemini WSL setup complete"
Write-Step "How to run Gemini"
Write-Host "1. Interactive mode:" -ForegroundColor Yellow
Write-Host "   .\scripts\ai\gemini\launch-gemini-wsl.ps1 start"
Write-Host "2. Execute a prompt with auto-approval:" -ForegroundColor Yellow
Write-Host "   .\scripts\ai\gemini\launch-gemini-wsl.ps1 exec `"review the current diff`""
Write-Host "3. Check environment after configuring .env.gemini:" -ForegroundColor Yellow
Write-Host "   .\scripts\ai\gemini\run-gemini.ps1 check"
