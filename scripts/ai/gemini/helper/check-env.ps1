#!/usr/bin/env pwsh
# Helper: Check Gemini environment by delegating to the canonical WSL check.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "wsl-support.ps1"
. $WslSupport

$RepoRootWin = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\..\.."))
$RepoWSL = ConvertTo-GeminiWslPath $RepoRootWin
$CheckWSL = "$RepoWSL/scripts/ai/gemini/helper/check-env.sh"

$exitCode = Invoke-GeminiWslBashScript -ScriptPath $CheckWSL
exit $exitCode
