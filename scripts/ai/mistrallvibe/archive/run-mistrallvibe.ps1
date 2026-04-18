#!/usr/bin/env pwsh
# Mistral-Vibe - Main Entry Point (Windows)
# Usage: .\run-mistrallvibe.ps1 [command] [args]
# Official Mistral Vibe - https://mistral.ai/vibe/

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$AllArgs
)

# Parse command and remaining args
$Command = if ($AllArgs.Count -gt 0) { $AllArgs[0] } else { "start" }
$Args = if ($AllArgs.Count -gt 1) { $AllArgs[1..($AllArgs.Count-1)] } else { @() }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperDir = Join-Path $ScriptDir "helper"
$RepoRoot = $PSScriptRoot

# Colors
$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mistral Vibe - Official Web UI" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Show help
if ($Command -eq "help" -or $Command -eq "-h" -or $Command -eq "--help") {
    Write-Host "Usage: .\run-mistrallvibe.ps1 [command] [args]" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  (no args)      Start Mistral Vibe"
    Write-Host "  start          Start Vibe server"
    Write-Host "  stop           Stop Vibe server"
    Write-Host "  status         Check Vibe status"
    Write-Host "  logs           View Vibe logs"
    Write-Host "  browser        Open browser to Vibe UI"
    Write-Host "  chat|cli       Interactive chat in console"
    Write-Host "  api-key        Show API key"
    Write-Host "  check          Check environment setup"
    Write-Host "  setup          Install Mistral Vibe"
    Write-Host "  help           Show this help"
    Write-Host ""
    Write-Host "Configuration:" -ForegroundColor Green
    Write-Host "  Edit .env.mistrallvibe for:"
    Write-Host "  - VIBE_API_KEY       Your Mistral API key"
    Write-Host "  - VIBE_PORT          Server port (default: 5173)"
    Write-Host "  - VIBE_HOST          Server host (default: localhost)"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\run-mistrallvibe.ps1 setup           # First time setup"
    Write-Host "  .\run-mistrallvibe.ps1 start           # Start server"
    Write-Host "  .\run-mistrallvibe.ps1 chat large      # Chat with large model"
    Write-Host "  .\run-mistrallvibe.ps1 api-key         # View your API key"
    Write-Host ""
    exit 0
}

# Handle chat/cli commands early (before Node.js check)
if ($Command -eq "chat" -or $Command -eq "cli") {
    Write-Info "Starting Mistral Vibe Chat CLI..."
    if ($Args.Count -gt 0) {
        Write-Info "Model: $($Args[0])"
    }
    Write-Host ""
    Push-Location $ScriptDir
    & python vibe-cli.py @Args
    Pop-Location
    exit $LASTEXITCODE
}

# Check Node.js for other commands
Write-Info "Checking Node.js installation..."
$nodeExists = $false
try {
    $nodeCheck = node --version 2>$null
    $nodeExists = $LASTEXITCODE -eq 0
} catch {
    $nodeExists = $false
}

if ($nodeExists) {
    Write-Success "Node.js found: $nodeCheck"
} else {
    Write-Warn "Node.js not found"
}

Write-Host ""

if (-not $nodeExists) {
    if ($Command -ne "setup") {
        Write-Warn "Node.js is required"
        Write-Info "Run setup first: .\run-mistrallvibe.ps1 setup"
        Write-Host ""
        exit 1
    }
}

# Process other commands
switch -Regex ($Command) {
    "^help|^-h|^--help$" {
        exit 0
    }
    
    "^start$|^$" {
        Write-Info "Starting Mistral Vibe..."
        Write-Host ""
        & "$HelperDir\run-mistrallvibe-impl.ps1" start @Args
    }
    
    "^stop$" {
        Write-Info "Stopping Mistral Vibe..."
        & "$HelperDir\run-mistrallvibe-impl.ps1" stop @Args
    }
    
    "^status$" {
        Write-Info "Checking Mistral Vibe status..."
        & "$HelperDir\run-mistrallvibe-impl.ps1" status @Args
    }
    
    "^logs$" {
        Write-Info "Viewing Mistral Vibe logs..."
        & "$HelperDir\run-mistrallvibe-impl.ps1" logs @Args
    }
    
    "^browser$" {
        Write-Info "Opening Mistral Vibe..."
        & "$HelperDir\run-mistrallvibe-impl.ps1" browser @Args
    }
    
    "^api-key$" {
        Write-Info "Showing API key..."
        & "$HelperDir\run-mistrallvibe-impl.ps1" api-key @Args
    }
    
    "^check$" {
        & "$HelperDir\check-env.ps1"
        exit 0
    }
    
    "^setup$" {
        Write-Info "Running Mistral Vibe setup..."
        Write-Host ""
        & "$HelperDir\setup-env.ps1"
        exit 0
    }
    
    default {
        Write-Error "Unknown command: $Command"
        Write-Info "Use '.\run-mistrallvibe.ps1 help' for usage"
        exit 1
    }
}

exit $LASTEXITCODE
