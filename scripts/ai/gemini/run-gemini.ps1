#!/usr/bin/env pwsh
# Gemini - Main Entry Point.
# Delegates all runtime logic to the canonical WSL launcher.

param(
    [string]$Command = "start",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

# Treat the process-scoped HTTP proxy as the canonical Gemini proxy. Keep the
# credential outside the tracked script and provide the aliases used by HTTPS
# and proxy-aware CLI clients before WSLENV forwards them to the launcher.
if (-not [string]::IsNullOrWhiteSpace($env:HTTP_PROXY)) {
    $env:HTTPS_PROXY = $env:HTTP_PROXY
    $env:ALL_PROXY = $env:HTTP_PROXY
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

$LauncherWSL = ConvertTo-GeminiWslPath (Join-Path $ScriptDir "run-gemini.sh")

if ($Command -match "^(help|-h|--help)$" -and $Prompt.Count -eq 0) {
    Write-Host @"
Usage: .\run-gemini.ps1 [command] [prompt...]

Delegates to the canonical WSL launcher at scripts/ai/gemini/run-gemini.sh.

Commands:
  (no args)      Start interactive Gemini
  start          Start interactive mode
  prompt         Send a single prompt
  exec           Auto-execute in headless mode (YOLO approvals)
  check          Check environment setup
  setup          Setup managed Gemini runtime
  mcp-check      Check Gemini MCP configuration
  mcp-setup      Sync Gemini MCP configuration
  update         Update managed Gemini runtime
  help           Show this help

Set BIOETL_WSL_DISTRO to target a specific WSL distro; otherwise the default
WSL distro is used.
"@
    exit 0
}

$ArgsToPass = @()

if ($MyInvocation.BoundParameters.ContainsKey("Command")) {
    $ArgsToPass += $Command
    $ArgsToPass += $Prompt
}

$exitCode = Invoke-GeminiWslBashScript -ScriptPath $LauncherWSL -Arguments $ArgsToPass
exit $exitCode
