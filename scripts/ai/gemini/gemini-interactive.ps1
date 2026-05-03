#!/usr/bin/env pwsh
# Gemini Interactive Launcher (PowerShell)
# Quick entry point for interactive Gemini CLI in WSL from Windows
# Usage: .\gemini-interactive.ps1 [prompt]

param(
    [string[]]$Arguments = @()
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

$LauncherWSL = "$RepoWSL/scripts/ai/gemini/gemini-interactive.sh"

if ($Arguments.Count -gt 0) {
    wsl -d Ubuntu -e bash -- "$LauncherWSL" @Arguments
} else {
    wsl -d Ubuntu -e bash -- "$LauncherWSL"
}

exit $LASTEXITCODE
