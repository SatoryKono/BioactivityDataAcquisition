#!/usr/bin/env pwsh
# Helper: Run Mistral Vibe operations on Windows
# Historical manager helper retained for compatibility only.

param(
    [string]$Command = "start",
    [string[]]$Args = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

# Load environment
$envFile = Join-Path $RootDir ".env.mistrallvibe"
$env:VIBE_PORT = "5173"
$env:VIBE_HOST = "localhost"
$env:VIBE_API_KEY = ""

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $varName = $matches[1]
            $varValue = $matches[2]
            [System.Environment]::SetEnvironmentVariable($varName, $varValue)
            Set-Variable -Name $varName -Value $varValue -Scope Script
        }
    }
}

$serverScript = Join-Path $RootDir "vibe-server.js"

# Function: Start Vibe
function Start-Vibe {
    Write-Info "Starting Mistral Vibe Server..."

    if ([string]::IsNullOrEmpty($env:VIBE_API_KEY) -or $env:VIBE_API_KEY -eq "your-api-key-here") {
        Write-Error "API key not configured in .env.mistrallvibe"
        Write-Info "Get your API key from: https://console.mistral.ai/api-keys/"
        return 1
    }

    # Check if node exists
    try {
        $nodeCheck = node --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Node.js is not installed"
            return 1
        }
    } catch {
        Write-Error "Node.js is not installed"
        return 1
    }

    if (-not (Test-Path $serverScript)) {
        Write-Error "vibe-server.js not found"
        return 1
    }

    Write-Info "Starting server on $env:VIBE_HOST`:$env:VIBE_PORT"
    Write-Info "Open http://$env:VIBE_HOST`:$env:VIBE_PORT in your browser"
    Write-Host ""

    Push-Location $RootDir
    & node vibe-server.js
    Pop-Location
}

# Function: Stop Vibe
function Stop-Vibe {
    Write-Info "Stopping Mistral Vibe..."

    $processes = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vibe-server.js*" }

    if ($processes) {
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Success "Vibe stopped"
    } else {
        Write-Warn "Vibe process not found"
    }
}

# Function: Check status
function Status-Vibe {
    Write-Info "Checking Mistral Vibe status..."
    Write-Host ""

    $processes = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vibe-server.js*" }

    if ($processes) {
        Write-Success "Vibe is RUNNING"
        Write-Info "Web UI: http://$env:VIBE_HOST`:$env:VIBE_PORT"
    } else {
        Write-Warn "Vibe is NOT running"
        Write-Info "Start with: .\run-vibe.ps1"
    }
}

# Function: Show logs
function Show-Logs {
    Write-Info "Vibe runs in foreground - check the terminal output above"
}

# Function: Show API key
function Show-ApiKey {
    Write-Info "Your Mistral Vibe API key:"
    Write-Host ""

    if ([string]::IsNullOrEmpty($env:VIBE_API_KEY) -or $env:VIBE_API_KEY -eq "your-api-key-here") {
        Write-Error "API key not configured"
        Write-Host ""
        Write-Info "1. Get key from: https://console.mistral.ai/api-keys/"
        Write-Info "2. Edit .env.mistrallvibe and set MISTRAL_API_KEY"
    } else {
        $keyLength = $env:VIBE_API_KEY.Length
        $prefix = $env:VIBE_API_KEY.Substring(0, [Math]::Min(10, $keyLength))
        $suffix = $env:VIBE_API_KEY.Substring([Math]::Max(0, $keyLength - 10))
        Write-Host "  $prefix...$suffix"
        Write-Info "Full key shown in .env.mistrallvibe"
    }
}

# Function: Open browser
function Open-Browser {
    Write-Info "Opening browser..."

    Start-Process "http://$env:VIBE_HOST`:$env:VIBE_PORT"
}

# Main dispatcher
switch ($Command) {
    "start" { Start-Vibe }
    "stop" { Stop-Vibe }
    "status" { Status-Vibe }
    "logs" { Show-Logs }
    "api-key" { Show-ApiKey }
    "browser" { Open-Browser }
    default {
        Write-Error "Unknown operation: $Command"
        exit 1
    }
}

exit $LASTEXITCODE
if ([string]::IsNullOrEmpty($env:VIBE_API_KEY) -and -not [string]::IsNullOrEmpty($env:MISTRAL_API_KEY)) {
    $env:VIBE_API_KEY = $env:MISTRAL_API_KEY
}
