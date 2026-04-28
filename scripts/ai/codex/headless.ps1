#!/usr/bin/env pwsh
# Canonical PowerShell transport for the Codex headless launcher.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslDistro = if ($env:BIOETL_WSL_DISTRO) { $env:BIOETL_WSL_DISTRO } else { "Ubuntu" }

function ConvertTo-WslPath {
    param([string]$WindowsPath)

    $drive = $WindowsPath.Substring(0, 1).ToLowerInvariant()
    $rest = $WindowsPath.Substring(2).Replace('\', '/')
    return "/mnt/$drive$rest"
}

$LauncherWSL = ConvertTo-WslPath (Join-Path $ScriptDir "headless.sh")

if ($Args.Count -gt 0 -and $Args[0] -match "^(help|-h|--help)$") {
    Write-Host @"
Usage: .\headless.ps1 [command] [prompt]

Delegates to the canonical WSL launcher at scripts/ai/codex/headless.sh and
skips MCP synchronization before launching Codex.
"@
    exit 0
}

wsl -d $WslDistro -e bash -- $LauncherWSL @Args
exit $LASTEXITCODE
