#!/usr/bin/env pwsh
# Canonical PowerShell transport for the Codex WSL launcher.

param(
    [string]$Command = "start",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

function Invoke-CodexInWsl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LauncherWSL,

        [string[]]$Arguments = @()
    )

    $wslExe = Get-CodexWslCommand
    if (-not $wslExe) {
        Write-Host "ERROR: wsl.exe was not found from this PowerShell session." -ForegroundColor Red
        Write-Host "Install WSL 2, restore C:\Windows\System32 in PATH, or verify with: where.exe wsl" -ForegroundColor Red
        return 1
    }

    $wslDistro = if ($env:BIOETL_WSL_DISTRO) {
        $env:BIOETL_WSL_DISTRO
    } else {
        ""
    }

    if ($wslDistro) {
        & $wslExe -d $wslDistro -e bash -- $LauncherWSL @Arguments
    } else {
        & $wslExe -e bash -- $LauncherWSL @Arguments
    }

    return $LASTEXITCODE
}

$LauncherWSL = ConvertTo-CodexWslPath (Join-Path $ScriptDir "run-codex.sh")

if ($Command -match "^(help|-h|--help)$" -and $Prompt.Count -eq 0) {
    Write-Host @"
Usage: .\run-codex.ps1 [command] [prompt...]

Delegates to the canonical WSL launcher at scripts/ai/codex/run-codex.sh.

Commands:
  (no args)      Start interactive Codex
  start          Start interactive mode
  exec           Auto-execute mode
  check          Check environment
  setup          Setup components
  mcp-check      Run bounded profile-aware MCP readiness checks
  mcp-static     Check MCP configuration without live services
  mcp-setup      Force-refresh MCP configuration
  login          Login with API key
  device-login   Device code auth
  help           Show this help

Set BIOETL_WSL_DISTRO to target a specific WSL distro; otherwise the default
WSL distro is used.
"@
    exit 0
}

$ArgsToPass = @()
if ($PSBoundParameters.ContainsKey("Command")) {
    $ArgsToPass += $Command
    $ArgsToPass += $Prompt
}

$exitCode = Invoke-CodexInWsl -LauncherWSL $LauncherWSL -Arguments $ArgsToPass
exit $exitCode
