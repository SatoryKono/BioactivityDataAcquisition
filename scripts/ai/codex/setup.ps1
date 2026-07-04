<#
.SYNOPSIS
    A comprehensive script to install and configure WSL2 and Codex.
.DESCRIPTION
    This script automates the entire setup process:
    1. Checks for and installs WSL2 and the Ubuntu distribution.
    2. Checks and configures .env.codex with an OpenAI API key.
    3. Runs the Codex setup scripts inside WSL.
    4. Provides diagnostics and feedback at each step.
    Run this script in an elevated (Administrator) PowerShell session.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot
$CanCreateEnvFile = $env:BIOETL_CREATE_LOCAL_ENV_FILES -eq "1"

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

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# ========================================================================
# Step 0: Check for Administrator privileges
# ========================================================================
Write-Header "Starting Codex Setup"
Write-Step "Step 0: Checking for Administrator privileges"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error-Message "This script requires Administrator privileges. Please re-run PowerShell as an Administrator."
    exit 1
}
Write-Success "Script is running with Administrator privileges."

# ========================================================================
# Step 1: WSL2 Installation
# ========================================================================
Write-Step "Step 1: Checking and installing WSL2"

try {
    $wslStatus = wsl --status
    Write-Success "WSL is already installed."
    Write-Host $wslStatus
}
catch {
    Write-Warning "WSL is not installed. Starting installation..."
    try {
        wsl --install
        Write-Success "WSL has been installed successfully. A computer RESTART is required."
        Write-Host "After rebooting, Ubuntu will start automatically and ask you to create a user and password."
        Write-Host "Then, run this script again to complete the setup."
        exit 0
    }
    catch {
        Write-Error-Message "Automatic WSL installation failed. Please follow the manual steps in WSL_SETUP_INSTRUCTIONS.md"
        exit 1
    }
}

# ========================================================================
# Step 2: Configure .env.codex
# ========================================================================
Write-Step "Step 2: Configuring .env.codex"
$envCodexPath = Join-Path -Path $ScriptDir -ChildPath ".env.codex"
$envExamplePath = Join-Path -Path $ScriptDir -ChildPath ".env.codex.example"

if (-not (Test-Path $envCodexPath)) {
    if (-not $CanCreateEnvFile) {
        Write-Error-Message ".env.codex not found. Create it manually, or rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 to generate a local template."
        exit 1
    }

    Write-Warning "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating .env.codex from example..."
    if (Test-Path $envExamplePath) {
        Copy-Item -Path $envExamplePath -Destination $envCodexPath
    }
    else {
        Write-Error-Message "Template file .env.codex.example not found!"
        exit 1
    }
}

$envContent = Get-Content $envCodexPath -Raw
# Check for modern (sk-proj-) or legacy (sk-) key formats.
if ($envContent -notmatch "OPENAI_API_KEY=sk-(proj-)?[a-zA-Z0-9]+") {
    Write-Warning "OPENAI_API_KEY not found or is invalid in .env.codex."
    if (-not $CanCreateEnvFile) {
        Write-Error-Message ".env.codex is not modified without BIOETL_CREATE_LOCAL_ENV_FILES=1. Edit it manually, or rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 to update it interactively."
        exit 1
    }

    $apiKey = Read-Host "Please enter your OpenAI API key (starts with sk-)"
    if ($apiKey -like "sk-*") {
        "OPENAI_API_KEY=$apiKey" | Set-Content -Path $envCodexPath
        Write-Success "API key has been saved to .env.codex."
    }
    else {
        Write-Error-Message "Invalid key entered. Please edit the .env.codex file manually and run the script again."
        exit 1
    }
}
else {
    Write-Success ".env.codex is configured with an API key."
}

# ========================================================================
# Step 3: Configure Codex environment in WSL
# ========================================================================
Write-Step "Step 3: Running Codex environment setup in WSL"
$setupBatPath = Join-Path -Path $ScriptDir -ChildPath "setup-codex-wsl.bat"

if (-not (Test-Path $setupBatPath)) {
    Write-Error-Message "Script setup-codex-wsl.bat not found!"
    exit 1
}

try {
    Write-Host "Executing $setupBatPath... This may take several minutes."
    # Execute the .bat via cmd.exe for more reliable output and exit code capturing.
    # This also helps avoid some permission and path issues that can occur with Start-Process.
    & cmd.exe /c "`"$setupBatPath`" /noninteractive"
    if ($LASTEXITCODE -ne 0) {
        throw "Script setup-codex-wsl.bat finished with an error. Code: $LASTEXITCODE"
    }
    Write-Success "Codex setup script completed successfully."
}
catch {
    Write-Error-Message "An error occurred while executing setup-codex-wsl.bat."
    Write-Error-Message "Please check the console output above for errors."
    Write-Error-Message "Details: $($_.Exception.Message)"
    Write-Host "You can try running diagnostics: .\launch-codex-wsl.ps1 check"
    exit 1
}

# ========================================================================
# Step 4: Completion
# ========================================================================
Write-Header "Codex installation and setup complete!"
Write-Step "How to run Codex:"
Write-Host "1. Interactive mode:" -ForegroundColor Yellow
Write-Host "   .\launch-codex-wsl.ps1 start"
Write-Host "2. Execute a command:" -ForegroundColor Yellow
Write-Host "   .\launch-codex-wsl.ps1 exec `"analyze the code`""
Write-Host "3. Check environment:" -ForegroundColor Yellow
Write-Host "   .\launch-codex-wsl.ps1 check"
