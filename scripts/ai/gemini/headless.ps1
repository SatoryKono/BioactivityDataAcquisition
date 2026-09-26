#!/usr/bin/env pwsh
# Canonical PowerShell transport for the Gemini headless launcher.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

$LauncherWSL = ConvertTo-GeminiWslPath (Join-Path $ScriptDir "headless.sh")

if ($Args.Count -gt 0 -and $Args[0] -match "^(help|-h|--help)$") {
    Write-Host @"
Usage: .\headless.ps1 [command] [prompt]

Delegates to the canonical WSL launcher at scripts/ai/gemini/headless.sh and
skips MCP synchronization before launching Gemini.

Set BIOETL_WSL_DISTRO to target a specific WSL distro; otherwise the default
WSL distro is used.
"@
    exit 0
}

$exitCode = Invoke-GeminiWslBashScript -ScriptPath $LauncherWSL -Arguments $Args
exit $exitCode
