#!/usr/bin/env pwsh
# Canonical PowerShell transport for WSL Codex launcher
# Properly handles output and arguments

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function ConvertTo-WslPath {
    param([string]$Path)
    $drive = $Path.Substring(0, 1).ToLowerInvariant()
    $rest = $Path.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

$LauncherWSL = (ConvertTo-WslPath $ScriptDir) + "/run-codex.sh"

# Show help
if ($Args.Count -gt 0 -and $Args[0] -match "^(help|-h|--help)$") {
    Write-Host @"
Usage: .\run-codex.ps1 [command] [prompt...]

Commands:
  (no args)      Start interactive Codex
  exec           Auto-execute mode
  check          Check environment
  setup          Setup components
  mcp-check      Check MCP configuration
  mcp-setup      Sync MCP configuration
  login          Login with API key
  device-login   Device code auth
  help           Show this help

Examples:
  .\run-codex.ps1
  .\run-codex.ps1 exec "analyze the code"
  .\run-codex.ps1 check
"@
    exit 0
}

# Resolve wsl.exe
$wsl = Get-Command wsl -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $wsl) {
    $wsl = Join-Path $env:WINDIR "System32\wsl.exe"
    if (-not (Test-Path $wsl)) {
        Write-Error "WSL not found. Install WSL2 or run from Linux/WSL."
        exit 1
    }
}

# Build command
$cmdArgs = if ($Args.Count -gt 0) { $Args -join ' ' } else { "" }
$bashCmd = "bash '$LauncherWSL' $cmdArgs"

# Get distro if specified
$distro = $env:BIOETL_WSL_DISTRO

# Run with proper output handling
try {
    if ($distro) {
        & $wsl -d $distro -e bash -c $bashCmd
    }
    else {
        & $wsl -e bash -c $bashCmd
    }
}
catch {
    Write-Error "WSL execution failed: $_"
    exit 1
}

exit $LASTEXITCODE
