#!/usr/bin/env pwsh
# Launch Mistral Vibe from Windows (via WSL) in the current repository.
# Usage: .\run-vibe.ps1 [args...]
#
# Examples:
#   .\run-vibe.ps1                      # Start interactive mode
#   .\run-vibe.ps1 "explain this code"  # Send prompt
#   .\run-vibe.ps1 --help               # Show vibe help

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir  # Go up from script-mistrallvibe to root

# Convert Windows path to WSL path
$WSLRepoRoot = $RepoRoot -replace '\\', '/' -replace '^([A-Z]):', '/mnt/$1' -replace '/mnt/([a-z])', '/mnt/${1}'
$WSLRepoRoot = $WSLRepoRoot.ToLower()

# Colors
$Colors = @{ Error = "Red"; Warning = "Yellow"; Info = "Cyan" }

function Write-MistralError { Write-Host "[vibe]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " ERROR: $args" }
function Write-MistralWarn { Write-Host "[vibe]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-MistralInfo { Write-Host "[vibe]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

# Check if WSL is available
$WSLExists = $false
try {
    $WSLCheck = wsl -e bash -c "echo ok" 2>$null
    $WSLExists = $LASTEXITCODE -eq 0
} catch {
    $WSLExists = $false
}

if (-not $WSLExists) {
    Write-MistralError "WSL (Windows Subsystem for Linux) not found"
    Write-Host "[vibe] Install WSL2 or use bash wrapper on Linux/macOS"
    exit 1
}

# Check if vibe is installed in WSL
$vibeExists = $false
try {
    $vibeVersion = wsl -e bash -c 'export PATH="$HOME/.local/bin:$PATH" && vibe --version' 2>$null
    $vibeExists = $LASTEXITCODE -eq 0
} catch {
    $vibeExists = $false
}

if (-not $vibeExists) {
    Write-MistralError "Mistral Vibe CLI not found in WSL"
    Write-Host "[vibe] Install with one of:"
    Write-Host "[vibe]   wsl -e bash -c 'curl -LsSf https://mistral.ai/vibe/install.sh | bash'"
    Write-Host "[vibe]   wsl -e bash -c 'python3 -m pip install --user mistral-vibe'"
    Write-Host "[vibe]   wsl -e bash -c 'pipx install mistral-vibe'"
    Write-Host "[vibe]"
    Write-Host "[vibe] Or run setup: .\run-vibe.ps1 setup"
    exit 1
}

# Get version
$vibeVersion = wsl -e bash -c 'export PATH="$HOME/.local/bin:$PATH" && vibe --version 2>/dev/null || echo "unknown"' 2>$null

Write-MistralInfo "Using Vibe $vibeVersion (via WSL)"
Write-MistralInfo "Working directory: $RepoRoot"

# Launch vibe via WSL
if ($Args.Count -eq 0) {
    Write-MistralInfo "Starting interactive mode..."
    wsl -e bash -c "export PATH=`$HOME/.local/bin:`$PATH && source `$HOME/.local/bin/env 2>/dev/null || true && vibe --workdir '$WSLRepoRoot'"
} else {
    $PromptText = $Args -join ' '
    Write-MistralInfo "Prompt: $PromptText"
    wsl -e bash -c "export PATH=`$HOME/.local/bin:`$PATH && source `$HOME/.local/bin/env 2>/dev/null || true && vibe --workdir '$WSLRepoRoot' '$PromptText'"
}

exit $LASTEXITCODE
