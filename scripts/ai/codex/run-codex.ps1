#!/usr/bin/env pwsh
# Codex - Main Entry Point
# Supports: check, setup, start, exec, login, mcp-check, mcp-setup, help

param(
    [string]$Command = "check",
    [string[]]$Prompt = @()
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
$WslDistro = if ($env:BIOETL_WSL_DISTRO) { $env:BIOETL_WSL_DISTRO } else { "Ubuntu" }

# Convert Windows path to WSL path
function ConvertTo-WslPath {
    param([string]$WindowsPath)
    
    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2) -replace '\\', '/'
    return "/mnt/$drive$rest"
}

$LauncherWSL = ConvertTo-WslPath $ScriptDir
$LauncherWSL = "$LauncherWSL/run-codex.sh"

# Build arguments
$args_list = @($Command)
if ($Prompt.Count -gt 0) {
    $args_list += $Prompt
}

# Show help
if ($Command -match "^(help|-h|--help)$") {
    Write-Host @"
Usage: .\run-codex.ps1 [command] [prompt]

Commands:
  check         Check environment setup
  setup         Install missing components
  start         Start interactive Codex (use launch-interactive.ps1)
  exec          Auto-execute (no confirmations)
  login         Login with API key
  mcp-check     Check MCP configuration
  mcp-setup     Sync MCP configuration
  help          Show this help

For interactive Codex mode:
  .\scripts\ai\codex\launch-interactive.ps1

Or run directly in WSL terminal:
  wsl bash -i -c 'cd /path/to/scripts/ai/codex && bash run-codex.sh'

Examples:
  .\run-codex.ps1 check
  .\run-codex.ps1 setup
  .\run-codex.ps1 exec "analyze the code"
"@
    exit 0
}

# Local diagnostics for check command
if ($Command -eq "check") {
    Write-Host ""
    Write-Host "=================================================="
    Write-Host "  Codex - Environment Check"
    Write-Host "=================================================="
    Write-Host ""

    $allOk = $true

    # Check Node.js
    Write-Host "[i] Checking Node.js..."
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $ver = node --version
        Write-Host "[+] Node.js: $ver"
    } else {
        Write-Host "[-] Node.js not found"
        $allOk = $false
    }

    # Check npm
    Write-Host "[i] Checking npm..."
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        $ver = npm --version
        Write-Host "[+] npm: $ver"
    } else {
        Write-Host "[-] npm not found"
        $allOk = $false
    }

    # Check WSL
    Write-Host "[i] Checking WSL..."
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        Write-Host "[+] WSL available"
    } else {
        Write-Host "[-] WSL not found"
        $allOk = $false
    }

    # Check .env.codex
    Write-Host "[i] Checking .env.codex..."
    $envFile = Join-Path $ScriptDir ".env.codex"
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "OPENAI_API_KEY.*sk-") {
            Write-Host "[+] .env.codex found with API key"
        } else {
            Write-Host "[!] .env.codex found but API key invalid"
            $allOk = $false
        }
    } else {
        Write-Host "[-] .env.codex not found"
        $allOk = $false
    }

    # Check Codex CLI in WSL
    Write-Host "[i] Checking Codex CLI in WSL..."
    try {
        $timeout_job = Start-Job -ScriptBlock {
            wsl -d Ubuntu bash -c "command -v codex >/dev/null 2>&1 && echo 'found' || echo 'not found'"
        }
        $result = Wait-Job -Job $timeout_job -Timeout 10 | Receive-Job
        Remove-Job -Job $timeout_job -Force 2>$null

        if ($result -like "*found*") {
            Write-Host "[+] Codex CLI found in WSL"
        } else {
            Write-Host "[!] Codex CLI not found in WSL"
            $allOk = $false
        }
    } catch {
        Write-Host "[!] Could not check Codex CLI"
        $allOk = $false
    }

    Write-Host ""
    if ($allOk) {
        Write-Host "[SUCCESS] All checks passed"
        exit 0
    } else {
        Write-Host "[!] Some components missing"
        Write-Host "[i] Run setup first: .\run-codex.ps1 setup"
        exit 1
    }
}

# Setup command
if ($Command -eq "setup") {
    Write-Host ""
    Write-Host "=================================================="
    Write-Host "  Codex - Setup"
    Write-Host "=================================================="
    Write-Host ""

    # Check if Node.js and npm exist
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "[-] Node.js not found"
        Write-Host "[!] Please install Node.js from https://nodejs.org"
        exit 1
    }

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "[-] npm not found"
        Write-Host "[!] Please reinstall Node.js"
        exit 1
    }

    Write-Host "[+] Node.js and npm are installed"
    Write-Host ""
    Write-Host "[i] Installing Codex CLI globally..."
    
    try {
        npm install -g @openai/codex 2>&1 | Write-Host
        Write-Host "[+] Codex CLI installed"
    } catch {
        Write-Host "[-] Failed to install Codex"
        exit 1
    }

    Write-Host ""
    Write-Host "=================================================="
    Write-Host "[+] Setup completed!"
    Write-Host ""
    Write-Host "NEXT: .\run-codex.ps1 check"
    exit 0
}

# Special handling for "start" command
if ($Command -eq "start") {
    Write-Host ""
    Write-Host "=================================================="
    Write-Host "  Codex - Interactive Mode"
    Write-Host "=================================================="
    Write-Host ""
    Write-Host "Note: PowerShell cannot provide a proper interactive terminal for Codex."
    Write-Host ""
    Write-Host "Use one of these options:"
    Write-Host ""
    Write-Host "  Option 1: Windows Terminal (Recommended)"
    Write-Host "    .\scripts\ai\codex\launch-interactive.ps1"
    Write-Host ""
    Write-Host "  Option 2: Direct WSL terminal"
    Write-Host "    wsl -d Ubuntu bash"
    Write-Host "    cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex"
    Write-Host "    bash run-codex.sh start"
    Write-Host ""
    Write-Host "  Option 3: WSL one-liner"
    Write-Host "    wsl -d Ubuntu bash -i -c 'cd $LauncherWSL && bash run-codex.sh start'"
    Write-Host ""
    exit 0
}

# For other commands, delegate to WSL (background execution)
Write-Host "[i] Launching Codex from WSL..."
Write-Host ""

try {
    $job = Start-Job -ScriptBlock {
        param($Distro, $Launcher, $Args)
        wsl -d $Distro -e bash -- $Launcher @Args 2>&1
    } -ArgumentList $WslDistro, $LauncherWSL, $args_list

    $timeout = 300  # 5 minutes
    $result = Wait-Job -Job $job -Timeout $timeout

    if ($result) {
        $output = Receive-Job -Job $job
        if ($output) { Write-Host $output }
        $exitCode = $job.ExitCode
    } else {
        Write-Host "[!] Command timed out after ${timeout}s"
        Stop-Job -Job $job -PassThru | Remove-Job -Force 2>$null
        $exitCode = 124
    }
} catch {
    Write-Host "[!] Error: $_"
    $exitCode = 1
} finally {
    Remove-Job -Job $job -Force 2>$null
}

exit $exitCode
