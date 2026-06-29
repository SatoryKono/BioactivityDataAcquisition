#!/usr/bin/env pwsh
# Headless launcher - skips MCP sync

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function ConvertTo-WslPath {
    param([string]$Path)
    $drive = $Path.Substring(0, 1).ToLowerInvariant()
    $rest = $Path.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

$LauncherWSL = (ConvertTo-WslPath $ScriptDir) + "/headless.sh"

# Show help
if ($Args.Count -gt 0 -and $Args[0] -match "^(help|-h|--help)$") {
    Write-Host @"
Usage: .\headless.ps1 [command] [prompt...]

Launches Codex without MCP synchronization.

Examples:
  .\headless.ps1
  .\headless.ps1 exec "your prompt"
"@
    exit 0
}

# Resolve wsl.exe
$wsl = Get-Command wsl -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $wsl) {
    $wsl = Join-Path $env:WINDIR "System32\wsl.exe"
    if (-not (Test-Path $wsl)) {
        Write-Error "WSL not found"
        exit 1
    }
}

# Build command
$cmdArgs = if ($Args.Count -gt 0) { $Args -join ' ' } else { "" }
$bashCmd = "bash '$LauncherWSL' $cmdArgs"

# Run
try {
    if ($env:BIOETL_WSL_DISTRO) {
        & $wsl -d $env:BIOETL_WSL_DISTRO -e bash -c $bashCmd
    }
    else {
        & $wsl -e bash -c $bashCmd
    }
}
catch {
    Write-Error "WSL execution failed: $_"
    exit 1
}

exit $LASTEXITCODE
