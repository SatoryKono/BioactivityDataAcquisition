#!/usr/bin/env pwsh
# Gemini Interactive Launcher (PowerShell)
# Quick entry point for interactive Gemini CLI in WSL from Windows.
# Usage: .\gemini-interactive.ps1 [prompt]

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments = @()
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

$RepoRootWin = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\.."))
$RepoWSL = ConvertTo-GeminiWslPath $RepoRootWin
$LauncherWSL = "$RepoWSL/scripts/ai/gemini/gemini-interactive.sh"

$exitCode = Invoke-GeminiWslBashScript -ScriptPath $LauncherWSL -Arguments $Arguments
exit $exitCode
