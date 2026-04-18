#!/usr/bin/env pwsh
# Gemini - Main Entry Point
# Usage: .\run-gemini.ps1 [command] [prompt]

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HelperDir = Join-Path $ScriptDir "helper"
$RepoWSL = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
$HelperWSL = "$RepoWSL/script-gemini/helper"
$InvocationHint = Resolve-Path -Relative -LiteralPath $MyInvocation.MyCommand.Path
$SetupHint = "$InvocationHint setup"

# Colors
$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Gemini - Google AI Assistant" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Show help
if ($Command -eq "help" -or $Command -eq "-h" -or $Command -eq "--help") {
    Write-Host "Usage: $InvocationHint [command] [prompt]" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  (no args)          Start interactive Gemini"
    Write-Host "  start              Start interactive mode"
    Write-Host "  check              Check environment setup"
    Write-Host "  setup              Setup missing components"
    Write-Host "  help               Show this help"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  $InvocationHint"
    Write-Host "  $InvocationHint 'what is AI?'"
    Write-Host "  $InvocationHint 'explain quantum computing'"
    Write-Host ""
    exit 0
}

# Check environment without blocking
Write-Info "Checking environment..."

# Quick Python3 check
$pythonExists = $false
try {
    wsl -d Ubuntu -- bash -lc 'command -v python3 >/dev/null 2>&1' 2>$null | Out-Null
    $pythonExists = $LASTEXITCODE -eq 0
} catch {
    $pythonExists = $false
}

# Quick Gemini SDK check
$geminiExists = $false
try {
    wsl -d Ubuntu -- bash -lc 'compgen -G "$HOME/.cache/tools/gemini-venv/lib/python*/site-packages/google/genai" >/dev/null || compgen -G "$HOME/.cache/tools/gemini-venv/lib/python*/site-packages/google/generativeai" >/dev/null' 2>$null | Out-Null
    $geminiExists = $LASTEXITCODE -eq 0
} catch {
    $geminiExists = $false
}

if ($pythonExists) {
    Write-Success "Python3 found"
} else {
    Write-Warn "Python3 not found"
}

if ($geminiExists) {
    Write-Success "Gemini Python SDK found"
} else {
    Write-Warn "Gemini Python SDK not found"
}

Write-Host ""

# If anything missing and not already running setup, prompt user
if (-not $pythonExists -or -not $geminiExists) {
    if ($Command -ne "setup") {
        Write-Warn "Some components missing"
        Write-Info "Run setup first: $SetupHint"
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
        Write-Info "Launching Gemini..."
        Write-Host ""
        if ($PromptStr) {
            wsl -d Ubuntu -e bash -- "$HelperWSL/run-gemini-impl.sh" -- $PromptStr
        } else {
            wsl -d Ubuntu -e bash -- "$HelperWSL/run-gemini-impl.sh"
        }
    }
    
    "^check$" {
        & (Join-Path $HelperDir "check-env.ps1")
        exit 0
    }
    
    "^setup$" {
        Write-Info "Running setup (this may take 2-3 minutes)..."
        Write-Warn "DO NOT CLOSE THIS WINDOW"
        Write-Host ""
        
        # Get Windows host IP for proxy
        $hostIP = wsl -d Ubuntu -- bash -lc 'ip route show default 2>/dev/null | cut -d" " -f3 | head -n 1' 2>$null
        $hostIP = ($hostIP | Out-String).Trim()
        
        # Run setup with proxy environment variables
        if ($hostIP) {
            Write-Info "Proxy host: $hostIP:3128"
            wsl -d Ubuntu -- bash -lc "export http_proxy=http://${hostIP}:3128 https_proxy=http://${hostIP}:3128; '$HelperWSL/setup-env.sh'"
        } else {
            wsl -d Ubuntu -e bash -- "$HelperWSL/setup-env.sh"
        }
        $setupExit = $LASTEXITCODE
        
        Write-Host ""
        if ($setupExit -eq 0) {
            Write-Success "Setup completed!"
            Write-Info "Now run: $InvocationHint"
        } else {
            Write-Error "Setup failed with exit code: $setupExit"
            Write-Info "Check WSL logs: wsl -d Ubuntu -- journalctl -xe"
        }
        exit $setupExit
    }
    
    default {
        # Treat first arg as prompt
        $FullPrompt = @($Command) + $Prompt
        Write-Info "Launching Gemini with prompt..."
        Write-Host ""
        wsl -d Ubuntu -e bash -- "$HelperWSL/run-gemini-impl.sh" -- ($FullPrompt -join ' ')
    }
}

exit $LASTEXITCODE
