#!/usr/bin/env pwsh
# Gemini - Main Entry Point.
# Delegates all runtime logic to the canonical WSL launcher.

param(
    [string]$Command = "start",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Prompt = @()
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslSupport = Join-Path $ScriptDir "helper\wsl-support.ps1"
. $WslSupport

$RepoRootWin = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\.."))
$RepoWSL = ConvertTo-GeminiWslPath $RepoRootWin
$LauncherWSL = "$RepoWSL/scripts/ai/gemini/run-gemini.sh"
$ArgsToPass = @()

if ($MyInvocation.BoundParameters.ContainsKey("Command")) {
    $ArgsToPass += $Command
    $ArgsToPass += $Prompt
}

$exitCode = Invoke-GeminiWslBashScript -ScriptPath $LauncherWSL -Arguments $ArgsToPass
exit $exitCode
