#!/usr/bin/env pwsh
# Codex - Main Entry Point
# Usage: .\run-codex.ps1 [command] [prompt]

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperDir = Join-Path $ScriptDir "helper"
$RepoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
$HelperWSL = "$RepoWSL/script-codex/helper"

# Colors
$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Codex - AI Code Assistant" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Show help
if ($Command -eq "help" -or $Command -eq "-h" -or $Command -eq "--help") {
    Write-Host "Usage: .\run-codex.ps1 [command] [prompt]" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  (no args)          Start interactive Codex"
    Write-Host "  start              Start interactive mode"
    Write-Host "  exec               Auto-execute (no confirmations)"
    Write-Host "  login              Login with API key"
    Write-Host "  device-login       Login with device auth"
    Write-Host "  check              Check environment setup"
    Write-Host "  setup              Setup missing components"
    Write-Host "  help               Show this help"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\run-codex.ps1"
    Write-Host "  .\run-codex.ps1 'analyze the code'"
    Write-Host "  .\run-codex.ps1 exec 'refactor the parser'"
    Write-Host "  .\run-codex.ps1 login"
    Write-Host ""
    exit 0
}

# Check environment without blocking
Write-Info "Checking environment..."

# Quick Node.js check
$nodeExists = $false
try {
    $nodeCheck = wsl -d Ubuntu -- bash -c "command -v node >/dev/null 2>&1 && echo OK" 2>$null
    $nodeExists = $nodeCheck -eq "OK"
} catch {
    $nodeExists = $false
}

# Quick Codex check
$codexExists = $false
try {
    $codexCheck = wsl -d Ubuntu -- bash -c "command -v codex >/dev/null 2>&1 && echo OK" 2>$null
    $codexExists = $codexCheck -eq "OK"
} catch {
    $codexExists = $false
}

if ($nodeExists) {
    Write-Success "Node.js found"
} else {
    Write-Warn "Node.js not found"
}

if ($codexExists) {
    Write-Success "Codex found"
} else {
    Write-Warn "Codex not found"
}

Write-Host ""

# If anything missing and not already running setup, prompt user
if (-not $nodeExists -or -not $codexExists) {
    if ($Command -ne "setup") {
        Write-Warn "Some components missing"
        Write-Info "Run setup first: .\run-codex.ps1 setup"
        Write-Host ""
        exit 1
    }
}

# Process command
$PromptStr = $Prompt -join " "

switch -Regex ($Command) {
    "^help|^-h|^--help$" {
        # Already handled above
        exit 0
    }
    
    "^start$|^$" {
        Write-Info "Launching Codex..."
        Write-Host ""
        if ($PromptStr) {
            wsl -d Ubuntu -e bash -- "$HelperWSL/run-codex-impl.sh" -- $PromptStr
        } else {
            wsl -d Ubuntu -e bash -- "$HelperWSL/run-codex-impl.sh"
        }
    }
    
    "^exec$" {
        if ($PromptStr) {
            Write-Info "Launching Codex in exec mode..."
            Write-Host ""
            wsl -d Ubuntu -e bash -- "$HelperWSL/run-codex-impl.sh" exec --full-auto -- $PromptStr
        } else {
            Write-Error "exec mode requires a prompt"
            exit 1
        }
    }
    
    "^login$" {
        Write-Info "Launching Codex login..."
        Write-Host ""
        wsl -d Ubuntu -- bash -c 'source ~/.bashrc && codex login'
    }
    
    "^device-login$" {
        Write-Info "Launching Codex device login..."
        Write-Host ""
        wsl -d Ubuntu -- bash -c 'source ~/.bashrc && codex login --device-auth'
    }
    
    "^check$" {
        & (Join-Path $HelperDir "check-env.ps1")
        exit 0
    }
    
    "^setup$" {
        Write-Info "Running setup (this may take 3-5 minutes)..."
        Write-Warn "DO NOT CLOSE THIS WINDOW"
        Write-Host ""
        
        wsl -d Ubuntu -e bash -- "$HelperWSL/setup-env.sh"
        $setupExit = $LASTEXITCODE
        
        Write-Host ""
        if ($setupExit -eq 0) {
            Write-Success "Setup completed!"
            Write-Info "Now run: .\run-codex.ps1"
        } else {
            Write-Error "Setup failed with exit code: $setupExit"
            Write-Info "Check WSL logs: wsl -d Ubuntu -- journalctl -xe"
        }
        exit $setupExit
    }
    
    default {
        # Treat first arg as prompt
        $FullPrompt = @($Command) + $Prompt
        Write-Info "Launching Codex with prompt..."
        Write-Host ""
        wsl -d Ubuntu -e bash -- "$HelperWSL/run-codex-impl.sh" -- ($FullPrompt -join ' ')
    }
}

exit $LASTEXITCODE
