#!/usr/bin/env pwsh
# Mistral Vibe - Interactive Launcher
# Opens Windows Terminal or direct WSL with interactive Vibe session

param(
    [string]$Command = "start"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WslDistro = if ($env:BIOETL_WSL_DISTRO) { $env:BIOETL_WSL_DISTRO } else { "Ubuntu" }
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..\..")).Path

# Convert Windows path to WSL path
function ConvertTo-WslPath {
    param([string]$WindowsPath)
    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

$RepoRootWSL = ConvertTo-WslPath $RepoRoot

Write-Host ""
Write-Host "=================================================="
Write-Host "  Mistral Vibe - Interactive Mode"
Write-Host "=================================================="
Write-Host ""

# Try to use Windows Terminal if available
$wt = Get-Command wt -ErrorAction SilentlyContinue

if ($wt) {
    Write-Host "[i] Opening Windows Terminal with Vibe..."
    Write-Host ""

    # Open new tab with wsl and run vibe
    $cmd = "wsl -d $WslDistro -e bash -i -c 'cd $RepoRootWSL && bash scripts/ai/vibe/launch.sh'"
    & wt -w 0 nt -d $ScriptDir pwsh -NoExit -Command $cmd

    exit $LASTEXITCODE
}

# Fallback: Direct WSL without Windows Terminal
Write-Host "[i] Windows Terminal not found, using direct WSL..."
Write-Host "[i] Note: Some interactive features may not work properly"
Write-Host ""
Write-Host "To get full interactive support, install Windows Terminal:"
Write-Host "  https://www.microsoft.com/store/productId/9N0DX20HK701"
Write-Host ""

# Try to launch directly with WSL
try {
    $process = Start-Process -FilePath "wsl" `
        -ArgumentList "-d", $WslDistro, "-e", "bash", "-i", "-c", "cd '$RepoRootWSL' && bash scripts/ai/vibe/launch.sh" `
        -NoNewWindow `
        -PassThru

    $process.WaitForExit()
    exit $process.ExitCode
} catch {
    Write-Host "[!] Error launching Vibe: $_"
    exit 1
}
