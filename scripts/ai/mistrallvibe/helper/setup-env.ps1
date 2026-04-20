#!/usr/bin/env pwsh
# Helper: Setup Mistral Vibe environment on Windows
# Downloads and installs official Mistral Vibe

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mistral Vibe Setup (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Node.js
Write-Info "STEP 1: Checking Node.js..."
try {
    $nodeVersion = node --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Node.js found: $nodeVersion"
    } else {
        Write-Error "Node.js not found"
        Write-Info "Install from: https://nodejs.org/"
        exit 1
    }
} catch {
    Write-Error "Node.js not found"
    Write-Info "Install from: https://nodejs.org/"
    exit 1
}

# Step 2: Check npm
Write-Info "STEP 2: Checking npm..."
try {
    $npmVersion = npm --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "npm found: $npmVersion"
    } else {
        Write-Error "npm not found"
        exit 1
    }
} catch {
    Write-Error "npm not found"
    exit 1
}

Write-Host ""

# Step 3: Create .env.mistrallvibe
Write-Info "STEP 3: Creating .env.mistrallvibe..."
$envFile = Join-Path $RootDir ".env.mistrallvibe"

if (Test-Path $envFile) {
    Write-Success ".env.mistrallvibe already exists"
} else {
    $envContent = @"
# Mistral Vibe Configuration
VIBE_API_KEY=your-api-key-here
VIBE_PORT=5173
VIBE_HOST=localhost
"@
    Set-Content -Path $envFile -Value $envContent
    Write-Warn ".env.mistrallvibe created - please add your Mistral API key"
}

Write-Host ""

# Step 4: Download Vibe installer script
Write-Info "STEP 4: Installing Mistral Vibe..."
Write-Warn "This will download and execute official Mistral installer"
Write-Host ""

try {
    # Download and execute installer
    $installerUrl = "https://mistral.ai/vibe/install.sh"
    Write-Info "Downloading from: $installerUrl"
    
    # For Windows, use powershell to download and execute
    $installerScript = Invoke-WebRequest -Uri $installerUrl -UseBasicParsing | Select-Object -ExpandProperty Content
    
    Write-Success "Mistral Vibe installer downloaded"
    Write-Info "Please run the installer manually or use WSL for automatic installation"
    Write-Host ""
    Write-Info "For WSL: wsl -e bash -c 'curl -LsSf https://mistral.ai/vibe/install.sh | bash'"
} catch {
    Write-Warn "Could not auto-download installer"
    Write-Info "Download manually from: https://mistral.ai/vibe/install.sh"
}

Write-Host ""

# Step 5: Display next steps
Write-Host "================================================" -ForegroundColor Cyan
Write-Success "Setup completed!"
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "Next steps:"
Write-Host "  1. Get your API key: https://console.mistral.ai/api-keys/"
Write-Host "  2. Edit .env.mistrallvibe and add VIBE_API_KEY"
Write-Host "  3. Start Vibe: .\run-vibe.ps1"
Write-Host ""

exit 0
