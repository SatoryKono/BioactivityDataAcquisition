#!/usr/bin/env pwsh
# Codex - Main Entry Point.
# Delegates all runtime logic to the canonical WSL launcher.

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRootWin = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\.."))
$WslDistro = if ($env:BIOETL_WSL_DISTRO) { $env:BIOETL_WSL_DISTRO } else { "Ubuntu" }

try {
    $RepoWSL = (
        wsl -d $WslDistro -- wslpath -a ($RepoRootWin -replace "\\", "/") 2>$null |
            Out-String
    ).Trim()
} catch {
    $RepoWSL = ""
}

if (-not $RepoWSL) {
    $DriveLetter = $RepoRootWin.Substring(0, 1).ToLowerInvariant()
    $DrivePath = $RepoRootWin.Substring(2) -replace "\\", "/"
    $RepoWSL = "/mnt/$DriveLetter$DrivePath"
}

$LauncherWSL = "$RepoWSL/scripts/ai/codex/run-codex.sh"
$ArgsToPass = @()

if ($MyInvocation.BoundParameters.ContainsKey("Command")) {
    $ArgsToPass += $Command
    $ArgsToPass += $Prompt
}

wsl -d $WslDistro -e bash -- "$LauncherWSL" @ArgsToPass
exit $LASTEXITCODE
