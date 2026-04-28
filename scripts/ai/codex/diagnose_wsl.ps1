#!/usr/bin/env pwsh
# Canonical PowerShell transport for Codex WSL diagnostics.

param(
    [switch]$Verbose = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslDistro = if ($env:BIOETL_WSL_DISTRO) { $env:BIOETL_WSL_DISTRO } else { "Ubuntu" }

function ConvertTo-WslPath {
    param([string]$WindowsPath)

    $drive = $WindowsPath.Substring(0, 1).ToLowerInvariant()
    $rest = $WindowsPath.Substring(2).Replace('\', '/')
    return "/mnt/$drive$rest"
}

$LauncherWSL = ConvertTo-WslPath (Join-Path $ScriptDir "diagnose_wsl.sh")
$ArgsList = @()
if ($Verbose) {
    $ArgsList += "--verbose"
}

wsl -d $WslDistro -e bash -- $LauncherWSL @ArgsList
exit $LASTEXITCODE
