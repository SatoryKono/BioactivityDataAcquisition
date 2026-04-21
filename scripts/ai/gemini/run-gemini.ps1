#!/usr/bin/env pwsh
# Gemini - Main Entry Point.
# Delegates all runtime logic to the canonical WSL launcher.

param(
    [string]$Command = "start",
    [string[]]$Prompt = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRootWin = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\.."))

try {
    $RepoWSL = (wsl -d Ubuntu -- wslpath -a ($RepoRootWin -replace "\\", "/") 2>$null | Out-String).Trim()
} catch {
    $RepoWSL = ""
}

if (-not $RepoWSL) {
    $DriveLetter = $RepoRootWin.Substring(0, 1).ToLowerInvariant()
    $DrivePath = $RepoRootWin.Substring(2) -replace "\\", "/"
    $RepoWSL = "/mnt/$DriveLetter$DrivePath"
}

$LauncherWSL = "$RepoWSL/scripts/ai/gemini/run-gemini.sh"
$ArgsToPass = @()

if ($MyInvocation.BoundParameters.ContainsKey("Command")) {
    $ArgsToPass += $Command
    $ArgsToPass += $Prompt
}

wsl -d Ubuntu -e bash -- "$LauncherWSL" @ArgsToPass
exit $LASTEXITCODE
