#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Simplified Codex launcher for WSL without hanging on interactive prompts.

.DESCRIPTION
    Launches Codex in WSL Ubuntu distro with non-interactive mode and skip-update behavior.

.PARAMETER Command
    Command to run: start, exec, check, setup, mcp-check, mcp-setup, login, device-login, help

.PARAMETER Prompt
    Optional prompt/arguments for exec mode

.EXAMPLE
    .\launch-codex-wsl.ps1 start
    .\launch-codex-wsl.ps1 exec "analyze my code"
    .\launch-codex-wsl.ps1 check
#>

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslDistro = "Ubuntu"
$CodexDir = "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex"

# Helper: Convert Windows path to WSL path
function ConvertTo-WslPath {
    param([string]$WindowsPath)
    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

# Helper: Show usage
function Show-Usage {
    @"
Usage: .\launch-codex-wsl.ps1 [command] [prompt]

Commands:
  start          Start interactive Codex (default)
  exec           Auto-execute (no confirmations)
  check          Check environment setup
  setup          Setup missing components
  mcp-check      Check MCP configuration
  mcp-setup      Sync MCP configuration
  login          Login with API key
  device-login   Login with device auth
  help           Show this help

Examples:
  .\launch-codex-wsl.ps1 start
  .\launch-codex-wsl.ps1 exec "analyze the code"
  .\launch-codex-wsl.ps1 check

Environment Variables:
  BIOETL_WSL_DISTRO  Override WSL distro (default: Ubuntu)
  OPENAI_API_KEY     Your OpenAI API key (set in .env.codex)
"@ | Write-Host
}

# Show help if requested
if ($Command -match "^(help|-h|--help)$") {
    Show-Usage
    exit 0
}

# Verify WSL is available
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Error "WSL is not installed or not in PATH. Please install WSL 2."
    exit 1
}

# Build command arguments
$CmdArgs = @($Command)
if ($Prompt.Count -gt 0) {
    $CmdArgs += $Prompt
}

Write-Host "🚀 Launching Codex in WSL ($WslDistro)..." -ForegroundColor Cyan
Write-Host "   Command: $Command" -ForegroundColor Gray

# Launch with skip-update and non-interactive flags
# Skip any npm update prompts with stdin redirection
$BashCmd = "cd $CodexDir && CODEX_SKIP_MCP_SETUP=0 bash ./run-codex.sh $($CmdArgs -join ' ')"

try {
    # Use echo "2" to auto-skip update prompt (option 2 = Skip)
    $process = wsl -d $WslDistro bash -c "echo '2' | $BashCmd"
    exit $LASTEXITCODE
}
catch {
    Write-Error "Failed to launch Codex: $_"
    exit 1
}
