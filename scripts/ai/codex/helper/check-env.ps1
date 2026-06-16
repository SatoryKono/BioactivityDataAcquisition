#!/usr/bin/env pwsh
# Helper: Check and setup Codex environment
# Called by: run-codex.ps1

param(
    [switch]$SkipSetup = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$HelperDir = Join-Path $ScriptDir "helper"
$RepoWin = (Resolve-Path (Join-Path $ScriptDir "..\..\..")).Path
$RepoWSL = $null
$CanCreateEnvFile = $env:BIOETL_CREATE_LOCAL_ENV_FILES -eq "1"

try {
    $RepoWSL = (wsl -d Ubuntu -- wslpath -a "$RepoWin" 2>$null | Select-Object -First 1).Trim()
} catch {
    $RepoWSL = $null
}

if (-not $RepoWSL) {
    $drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
    $pathPart = $RepoWin.Substring(2).Replace('\', '/')
    $RepoWSL = "/mnt/$drive$pathPart"
}

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
Write-Host "  Codex Environment Check" -ForegroundColor Cyan
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

# 2. Check API Key in .env.codex
Log-Info "Checking API key..."
$EnvFile = Join-Path $RootDir ".env.codex"
if (Test-Path $EnvFile) {
    $Content = Get-Content $EnvFile
    if ($Content -match "OPENAI_API_KEY=sk-") {
        Log-Success "API key found in .env.codex"
    } else {
        Log-Warn ".env.codex exists but API key missing or invalid"
        $AllChecks = $false
    }
} else {
    Log-Warn ".env.codex not found"
    $AllChecks = $false
}

# 3. Check Node.js in WSL
Log-Info "Checking Node.js..."
$nodeCheck = wsl -- node --version 2>$null
if ($?) {
    Log-Success "Node.js is installed: $(wsl -- node --version)"
} else {
    Log-Warn "Node.js not found in WSL"
    if (-not $SkipSetup) {
        Log-Info "Will install Node.js automatically"
    }
}

# 4. Check Codex binary
Log-Info "Checking Codex CLI..."
$CodexBinWSL = "$RepoWSL/.cache/tools/codex-cli/npm-global/bin/codex"
$codexCheck = wsl -- bash -lc "test -x `"$CodexBinWSL`" && echo OK" 2>$null
if ($codexCheck -eq "OK") {
    Log-Success "Codex CLI is installed"
} else {
    Log-Warn "Codex CLI not found"
    if (-not $SkipSetup) {
        Log-Info "Will install Codex CLI automatically"
    }
}

# 5. Check .env.codex file exists
if (-not (Test-Path $EnvFile)) {
    if (-not $CanCreateEnvFile) {
        Log-Warn ".env.codex not found; not creating it without BIOETL_CREATE_LOCAL_ENV_FILES=1"
    } else {
        Log-Warn "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.codex template..."
        @(
            "# OpenAI Codex Configuration",
            "# Get your API key from: https://platform.openai.com/api-keys",
            "OPENAI_API_KEY=sk-your-key-here"
        ) | Set-Content $EnvFile
        Log-Success ".env.codex created - please edit and add your API key"
    }
}

Write-Host ""

# Return status
@{
    AllChecks = $AllChecks
    RootDir = $RootDir
    HelperDir = $HelperDir
    EnvFile = $EnvFile
}
