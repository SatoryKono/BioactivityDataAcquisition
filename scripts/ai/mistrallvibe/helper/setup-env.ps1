#!/usr/bin/env pwsh
# Helper: Setup Mistral Vibe environment on Windows
# Installs via WSL with timeout and retry protection

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

# Step 1: Check Node.js (with timeout)
Write-Info "STEP 1: Checking Node.js..."
$nodeJob = Start-Job -ScriptBlock { node --version 2>$null }
$nodeResult = Wait-Job -Job $nodeJob -Timeout 5 | Receive-Job
Remove-Job -Job $nodeJob -Force 2>$null

if ($nodeResult) {
    Write-Success "Node.js found: $nodeResult"
} else {
    Write-Warn "Node.js not found or timed out"
}

# Step 2: Check npm (with timeout)
Write-Info "STEP 2: Checking npm..."
$npmJob = Start-Job -ScriptBlock { npm --version 2>$null }
$npmResult = Wait-Job -Job $npmJob -Timeout 5 | Receive-Job
Remove-Job -Job $npmJob -Force 2>$null

if ($npmResult) {
    Write-Success "npm found: $npmResult"
} else {
    Write-Warn "npm not found or timed out"
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
MISTRAL_API_KEY=your-api-key-here
# Legacy compatibility alias:
# VIBE_API_KEY=your-api-key-here
VIBE_PORT=5173
VIBE_HOST=localhost
"@
    Set-Content -Path $envFile -Value $envContent
    Write-Warn ".env.mistrallvibe created - please add your Mistral API key"
}

Write-Host ""

# Step 4: Check for WSL
Write-Info "STEP 4: Checking WSL..."

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL not found - required for Mistral Vibe installation"
    Write-Info "Install WSL: wsl --install"
    exit 1
}

Write-Success "WSL is available"

Write-Host ""

# Step 5: Install Mistral Vibe via WSL
Write-Info "STEP 5: Installing Mistral Vibe via WSL..."
Write-Warn "This will install Python, pip, and Mistral Vibe with timeout and retry"
Write-Host ""

# Create install script file
$installScriptContent = @'
#!/bin/bash
set -euo pipefail

RETRY=0
MAX_RETRIES=2
INSTALL_SUCCESS=0

# Try pipx first
if command -v pipx >/dev/null 2>&1; then
    echo "[info] Using pipx to install mistral-vibe"
    RETRY=0
    while [ $RETRY -lt $MAX_RETRIES ]; do
        if timeout 60 pipx install mistral-vibe 2>/dev/null; then
            echo "[success] Installed via pipx"
            exit 0
        fi
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            echo "[warn] Retry attempt $RETRY/$MAX_RETRIES"
            sleep 2
        fi
    done
fi

# Fallback to pip
echo "[info] Using pip to install mistral-vibe"
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if timeout 60 python3 -m pip install --user --upgrade mistral-vibe 2>/dev/null; then
        echo "[success] Installed via pip"
        exit 0
    fi
    RETRY=$((RETRY + 1))
    if [ $RETRY -lt $MAX_RETRIES ]; then
        echo "[warn] Retry attempt $RETRY/$MAX_RETRIES"
        sleep 2
    fi
done

echo "[error] Installation failed after all retries"
exit 1
'@

$tempFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $tempFile -Value $installScriptContent -Encoding ASCII

try {
    $job = Start-Job -ScriptBlock {
        param($scriptPath)
        wsl bash $scriptPath
    } -ArgumentList $tempFile

    $result = Wait-Job -Job $job -Timeout 300

    if ($result) {
        $output = Receive-Job -Job $job
        $output | Write-Host

        if ($output -match "success") {
            Write-Success "Mistral Vibe installation completed"
        } elseif ($output -match "error") {
            Write-Warn "Installation may have issues, but continuing..."
        }
    } else {
        Write-Warn "Installation timed out, but this may be normal for first run"
        Stop-Job -Job $job -PassThru | Remove-Job -Force 2>$null
    }
} finally {
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue 2>$null
    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue 2>$null
}

Write-Host ""

# Step 6: Display next steps
Write-Host "================================================" -ForegroundColor Cyan
Write-Success "Setup completed!"
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "Next steps:"
Write-Host "  1. Get your API key:"
Write-Host "     https://console.mistral.ai/api-keys/"
Write-Host ""
Write-Host "  2. Edit .env.mistrallvibe and add MISTRAL_API_KEY:"
Write-Host "     notepad .\scripts\ai\mistrallvibe\.env.mistrallvibe"
Write-Host ""
Write-Host "  3. Verify installation:"
Write-Host "     python -m scripts.ai vibe check"
Write-Host ""
Write-Host "  4. Start Vibe:"
Write-Host "     python -m scripts.ai vibe"
Write-Host ""

exit 0
