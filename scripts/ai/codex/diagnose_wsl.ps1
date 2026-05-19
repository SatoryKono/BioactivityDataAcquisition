#!/usr/bin/env pwsh
# Canonical PowerShell transport for Codex WSL diagnostics.

param(
    [switch]$Verbose = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

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

if ($env:BIOETL_WSL_DISTRO) {
    wsl -d $env:BIOETL_WSL_DISTRO -e bash -- $LauncherWSL @ArgsList
}
else {
    wsl -e bash -- $LauncherWSL @ArgsList
}
exit $LASTEXITCODE
