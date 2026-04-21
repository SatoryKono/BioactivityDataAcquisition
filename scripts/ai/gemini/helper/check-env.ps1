#!/usr/bin/env pwsh
# Helper: Check Gemini environment by delegating to the canonical WSL check.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRootWin = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\..\.."))

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

$CheckWSL = "$RepoWSL/scripts/ai/gemini/helper/check-env.sh"
wsl -d Ubuntu -e bash -- "$CheckWSL"
exit $LASTEXITCODE
