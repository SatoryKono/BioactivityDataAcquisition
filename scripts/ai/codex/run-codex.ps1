#!/usr/bin/env pwsh
# Thin PowerShell transport for the canonical WSL/Bash Codex launcher.

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function ConvertTo-WslPath {
    param([string]$WindowsPath)

    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

$LauncherWSL = (ConvertTo-WslPath $ScriptDir) + "/run-codex.sh"

function Show-Usage {
    Write-Host @"
Usage: .\run-codex.ps1 [command] [prompt]

This PowerShell entrypoint is a thin transport over the canonical WSL/Bash launcher:
  bash run-codex.sh [command] [prompt]

Commands:
  (no args)      Start interactive Codex
  start          Start interactive mode
  exec           Auto-execute (no confirmations)
  login          Login with API key
  device-login   Login with device auth
  check          Check environment setup
  setup          Setup missing components
  mcp-check      Check Codex MCP configuration
  mcp-setup      Sync Codex MCP configuration
  help           Show this help

Examples:
  .\run-codex.ps1
  .\run-codex.ps1 exec "analyze the code"
  .\run-codex.ps1 mcp-setup
"@
}

function Resolve-WslExecutable {
    $wsl = Get-Command wsl -ErrorAction SilentlyContinue
    if ($wsl) {
        return $wsl.Source
    }

    $fallback = Join-Path $env:WINDIR "System32\wsl.exe"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    return $null
}

function Invoke-CodexInWsl {
    param([string[]]$LauncherArgs)

    $wslExe = Resolve-WslExecutable
    if (-not $wslExe) {
        Write-Error (
            "WSL is required for run-codex.ps1. Install WSL or run bash run-codex.sh from Linux/WSL."
        )
        return 1
    }

    $wslDistro = $env:BIOETL_WSL_DISTRO
    if ($wslDistro) {
        & $wslExe -d $wslDistro -e bash -- $LauncherWSL @LauncherArgs
    }
    else {
        & $wslExe -e bash -- $LauncherWSL @LauncherArgs
    }
    if ($LASTEXITCODE -ne $null) {
        return $LASTEXITCODE
    }
    return 0
}

if ($Command -match "^(help|-h|--help)$") {
    Show-Usage
    exit 0
}

$ArgsList = @($Command)
if ($Prompt.Count -gt 0) {
    $ArgsList += $Prompt
}

exit (Invoke-CodexInWsl -LauncherArgs $ArgsList)
