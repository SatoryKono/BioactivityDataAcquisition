#!/usr/bin/env pwsh
# Canonical Vibe launcher from Windows (via WSL).

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

if ($Args.Count -gt 0 -and ($Args[0] -eq "--help" -or $Args[0] -eq "-h")) {
    Write-Host "Mistral Vibe Launcher"
    Write-Host ""
    Write-Host "Usage: .\launch.ps1 [args...]"
    exit 0
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

$WSLRepoRoot = $RepoRoot -replace '\\', '/' -replace '^([A-Z]):', '/mnt/$1'
$WSLRepoRoot = $WSLRepoRoot.ToLower()
$CompatEnvWSL = "$WSLRepoRoot/scripts/ai/mistrallvibe/.env.mistrallvibe"
$ProxyEnvWSL = "$WSLRepoRoot/.wsl_proxy_env.sh"

$Colors = @{ Error = "Red"; Warning = "Yellow"; Info = "Cyan" }

function Write-MistralError { Write-Host "[mistral]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " ERROR: $args" }
function Write-MistralInfo { Write-Host "[mistral]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

$WSLExists = $false
try {
    $WSLCheck = wsl -e bash -c "echo ok" 2>$null
    $WSLExists = $LASTEXITCODE -eq 0
} catch {
    $WSLExists = $false
}

if (-not $WSLExists) {
    Write-MistralError "WSL (Windows Subsystem for Linux) not found"
    Write-Host "[mistral] Install WSL2 or use bash wrapper on Linux/macOS"
    exit 1
}

$vibeExists = $false
try {
    $vibeVersion = wsl -e bash -c 'export PATH="$HOME/.local/bin:$PATH" && vibe --version' 2>$null
    $vibeExists = $LASTEXITCODE -eq 0
} catch {
    $vibeExists = $false
}

if (-not $vibeExists) {
    Write-MistralError "Mistral Vibe CLI not found in WSL"
    Write-Host "[mistral] Install with one of:"
    Write-Host "[mistral]   wsl -e bash -c 'curl -LsSf https://mistral.ai/vibe/install.sh | bash'"
    Write-Host "[mistral]   wsl -e bash -c 'python3 -m pip install --user mistral-vibe'"
    Write-Host "[mistral]   wsl -e bash -c 'pipx install mistral-vibe'"
    exit 1
}

$vibeVersion = wsl -e bash -c 'export PATH="$HOME/.local/bin:$PATH" && vibe --version 2>/dev/null || echo "unknown"' 2>$null

Write-MistralInfo "Using Vibe $vibeVersion (via WSL)"
Write-MistralInfo "Working directory: $RepoRoot"

$EnvPrelude = @(
    'export PATH="$HOME/.local/bin:$PATH"',
    'source "$HOME/.local/bin/env" 2>/dev/null || true',
    "source '$ProxyEnvWSL' 2>/dev/null || true",
    "if [ -f '$CompatEnvWSL' ]; then set -a; source '$CompatEnvWSL' 2>/dev/null || true; set +a; fi",
    'if [ -n "${VIBE_API_KEY:-}" ] && [ -z "${MISTRAL_API_KEY:-}" ]; then export MISTRAL_API_KEY="$VIBE_API_KEY"; fi'
) -join ' && '

if ($Args.Count -eq 0) {
    Write-MistralInfo "Starting interactive mode..."
    wsl -e bash -c "$EnvPrelude && vibe --workdir '$WSLRepoRoot'"
} else {
    $PromptText = $Args -join ' '
    Write-MistralInfo "Prompt: $PromptText"
    wsl -e bash -c "$EnvPrelude && vibe --workdir '$WSLRepoRoot' '$PromptText'"
}

exit $LASTEXITCODE
