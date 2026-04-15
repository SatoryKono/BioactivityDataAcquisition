# gemini.ps1
# PowerShell wrapper for Gemini interactive launcher
# Run from PowerShell or Windows Terminal in project root
# Usage: .\scripts\ai\gemini.ps1 [interactive|setup|sync|status]

param(
    [Parameter(Position = 0)]
    [ValidateSet('interactive', 'setup', 'sync', 'status', 'help')]
    [string]$Command = 'interactive',
    
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

# Get project root
$projectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$geminiHome = Join-Path $projectRoot '.gemini'
$scriptsAiDir = Split-Path $PSScriptRoot

# WSL detection
function Test-WSLAvailable {
    try {
        $wslCheck = wsl --version 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Convert-ToWSLPath {
    param([string]$WindowsPath)
    $wslPath = wsl wslpath -a $WindowsPath 2>$null
    return $wslPath
}

# Colors
$colors = @{
    Green  = 'Green'
    Red    = 'Red'
    Yellow = 'Yellow'
    Cyan   = 'Cyan'
    Blue   = 'Blue'
    Magenta = 'Magenta'
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $colors.Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $colors.Red
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $colors.Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor $colors.Cyan
}

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "▶ $Message" -ForegroundColor $colors.Blue
    Write-Host ""
}

function Show-Help {
    Write-Host @"
🚀 Gemini Interactive Launcher (PowerShell)

Usage: .\scripts\ai\gemini.ps1 [command]

Commands:
  interactive    Launch interactive menu (default)
  setup          Initialize Gemini environment
  sync           Sync profiles from Codex
  status         Show environment status
  help           Show this help

Examples:
  .\scripts\ai\gemini.ps1
  .\scripts\ai\gemini.ps1 interactive
  .\scripts\ai\gemini.ps1 status
  .\scripts\ai\gemini.ps1 setup

Note: Requires WSL and bash to be available.

"@
}

function Test-Environment {
    Write-Section "Checking Environment"
    
    $ready = $true
    
    # Check Gemini home
    if (Test-Path $geminiHome) {
        Write-Success "Gemini home: $geminiHome"
    }
    else {
        Write-Error-Custom "Gemini home not found: $geminiHome"
        $ready = $false
    }
    
    # Check config files
    $configPath = Join-Path $geminiHome 'config.toml'
    $settingsPath = Join-Path $geminiHome 'settings.json'
    
    if (Test-Path $configPath) {
        Write-Success "Config: $(Split-Path $configPath -Leaf)"
    }
    else {
        Write-Error-Custom "Config not found"
        $ready = $false
    }
    
    if (Test-Path $settingsPath) {
        Write-Success "MCP settings: $(Split-Path $settingsPath -Leaf)"
    }
    else {
        Write-Error-Custom "MCP settings not found"
        $ready = $false
    }
    
    # Check WSL
    if (Test-WSLAvailable) {
        Write-Success "WSL available"
    }
    else {
        Write-Error-Custom "WSL not available (required for bash scripts)"
        $ready = $false
    }
    
    return $ready
}

function Launch-Interactive {
    Write-Section "Launching Gemini Interactive Menu"
    
    if (-not (Test-Environment)) {
        Write-Error-Custom "Environment check failed"
        Write-Host ""
        Write-Info "Run setup: .\scripts\ai\gemini.ps1 setup"
        return
    }
    
    # Convert path for WSL
    $bashScript = $scriptsAiDir -replace '\\', '/' -replace '^([A-Z]):', { $args[0].Groups[1].Value.ToLower() }
    $bashScript = "/mnt/$($bashScript[0])$($bashScript.Substring(1))/gemini-interactive.sh"
    
    Write-Info "Starting interactive menu in WSL..."
    Write-Host ""
    
    # Launch bash script in WSL
    wsl bash $bashScript
}

function Run-Setup {
    Write-Section "Running Gemini Setup"
    
    $setupScript = Join-Path $scriptsAiDir 'setup-gemini-wsl.sh'
    
    if (-not (Test-Path $setupScript)) {
        Write-Error-Custom "Setup script not found: $setupScript"
        return
    }
    
    Write-Info "Initializing Gemini environment..."
    Write-Host ""
    
    wsl bash $setupScript
}

function Run-Sync {
    Write-Section "Syncing Agent Profiles"
    
    $syncScript = Join-Path $scriptsAiDir 'sync-agents-codex-to-gemini.sh'
    
    if (-not (Test-Path $syncScript)) {
        Write-Error-Custom "Sync script not found: $syncScript"
        return
    }
    
    Write-Info "Syncing profiles from Codex to Gemini..."
    Write-Host ""
    
    wsl bash $syncScript
}

function Show-Status {
    Write-Section "Gemini Environment Status"
    
    $config = Join-Path $geminiHome 'config.toml'
    $settings = Join-Path $geminiHome 'settings.json'
    $memory = Join-Path $projectRoot 'docs/00-project/ai/memory/gemini-memory.json'
    $sessions = Join-Path $projectRoot 'docs/00-project/ai/sessions'
    
    Write-Host "Gemini Home: $geminiHome"
    (Test-Path $config) ? (Write-Success "Config exists") : (Write-Error-Custom "Config missing")
    (Test-Path $settings) ? (Write-Success "Settings exists") : (Write-Error-Custom "Settings missing")
    (Test-Path $memory) ? (Write-Success "Memory file exists") : (Write-Warning-Custom "Memory file will be created")
    (Test-Path $sessions) ? (Write-Success "Sessions directory exists") : (Write-Warning-Custom "Sessions directory will be created")
    
    Write-Host ""
    
    # Count profiles
    $profiles = @(Get-ChildItem (Join-Path $geminiHome 'agents') -Filter 'py-*.md' -ErrorAction SilentlyContinue).Count
    Write-Host "Agent profiles: $profiles"
    
    # Count sessions
    $sessionFiles = @(Get-ChildItem $sessions -Filter '*' -ErrorAction SilentlyContinue).Count
    Write-Host "Sessions: $sessionFiles"
    
    Write-Host ""
}

# Main command dispatcher
switch ($Command) {
    'interactive' {
        Launch-Interactive
    }
    'setup' {
        Run-Setup
    }
    'sync' {
        Run-Sync
    }
    'status' {
        Show-Status
    }
    'help' {
        Show-Help
    }
    default {
        Write-Error-Custom "Unknown command: $Command"
        Write-Host ""
        Show-Help
    }
}
