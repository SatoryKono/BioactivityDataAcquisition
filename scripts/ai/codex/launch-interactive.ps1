#!/usr/bin/env pwsh
# Codex - Interactive Launcher
# Opens Windows Terminal or direct WSL with interactive Codex session

param(
    [string]$Command = "start"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslDistro = if ($env:BIOETL_WSL_DISTRO) { $env:BIOETL_WSL_DISTRO } else { "Ubuntu" }

# Convert Windows path to WSL path
function ConvertTo-WslPath {
    param([string]$WindowsPath)
    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

$ScriptPathWSL = ConvertTo-WslPath $ScriptDir

Write-Host ""
Write-Host "=================================================="
Write-Host "  Codex - Interactive Mode"
Write-Host "=================================================="
Write-Host ""

# Try to use Windows Terminal if available
$wt = Get-Command wt -ErrorAction SilentlyContinue

if ($wt) {
    Write-Host "[i] Opening Windows Terminal with Codex..."
    Write-Host ""
    
    # Open new tab with wsl and run codex
    $cmd = "wsl -d $WslDistro -e bash -i -c 'cd $ScriptPathWSL && bash run-codex.sh start'"
    & wt -w 0 nt -d $ScriptDir powershell -NoExit -Command $cmd
    
    exit $LASTEXITCODE
}

# Fallback: Direct WSL without Windows Terminal
Write-Host "[i] Windows Terminal not found, using direct WSL..."
Write-Host "[i] Note: Some interactive features may not work properly"
Write-Host ""
Write-Host "To get full interactive support, install Windows Terminal:"
Write-Host "  https://www.microsoft.com/store/productId/9N0DX20HK701"
Write-Host ""

# Launch directly in the current terminal to preserve interactive TTY.
try {
    & wsl -d $WslDistro -e bash -i -c "cd '$ScriptPathWSL' && bash run-codex.sh start"
    exit $LASTEXITCODE
} catch {
    Write-Host "[!] Error launching Codex: $_"
    exit 1
}
