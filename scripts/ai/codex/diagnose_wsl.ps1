#!/usr/bin/env pwsh
# Canonical PowerShell transport for Codex WSL diagnostics.

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

$LauncherWSL = ConvertTo-CodexWslPath (Join-Path $ScriptDir "diagnose_wsl.sh")
$ArgsList = @()
if ($Verbose) {
    $ArgsList += "--verbose"
}

$exitCode = Invoke-CodexWslScript -ScriptPath $LauncherWSL -Arguments $ArgsList
exit $exitCode
