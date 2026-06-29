#!/usr/bin/env pwsh
# Shared WSL helpers for Codex PowerShell launchers.

$script:CodexWslDistro = if ($env:BIOETL_WSL_DISTRO) {
    $env:BIOETL_WSL_DISTRO
} else {
    ""
}
$script:CodexWslCommand = $null

function Get-CodexWslCommand {
    if ($script:CodexWslCommand -and (Test-Path $script:CodexWslCommand)) {
        return $script:CodexWslCommand
    }

    foreach ($commandName in @("wsl.exe", "wsl")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) {
            $script:CodexWslCommand = $command.Source
            return $script:CodexWslCommand
        }
    }

    $windowsRoots = @()
    if ($env:WINDIR) {
        $windowsRoots += $env:WINDIR
    }
    if ($env:SystemRoot -and ($env:SystemRoot -notin $windowsRoots)) {
        $windowsRoots += $env:SystemRoot
    }

    foreach ($windowsRoot in $windowsRoots) {
        foreach ($candidate in @(
            (Join-Path $windowsRoot "System32\wsl.exe"),
            (Join-Path $windowsRoot "Sysnative\wsl.exe")
        )) {
            if (Test-Path $candidate) {
                $script:CodexWslCommand = $candidate
                return $script:CodexWslCommand
            }
        }
    }

    return $null
}

function Get-CodexWslDistroArgs {
    if ($script:CodexWslDistro) {
        return @("-d", $script:CodexWslDistro)
    }
    return @()
}

function ConvertTo-CodexWslPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowsPath
    )

    $resolved = ""
    $wslCommand = Get-CodexWslCommand
    try {
        if ($wslCommand) {
            $wslArgs = @()
            $wslArgs += Get-CodexWslDistroArgs
            $wslArgs += @("--", "wslpath", "-a", $WindowsPath)
            $resolved = (& $wslCommand @wslArgs 2>$null | Out-String).Trim()
        }
    } catch {
        $resolved = ""
    }

    if ($resolved) {
        return $resolved
    }

    if ($WindowsPath -notmatch "^[A-Za-z]:") {
        throw "Cannot convert non-drive Windows path to WSL path: $WindowsPath"
    }

    $drive = $WindowsPath.Substring(0, 1).ToLowerInvariant()
    $rest = $WindowsPath.Substring(2).Replace("\", "/")
    return "/mnt/$drive$rest"
}

function Invoke-CodexWslScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [string[]]$Arguments = @()
    )

    $wslExe = Get-CodexWslCommand
    if (-not $wslExe) {
        Write-Host "ERROR: wsl.exe was not found from this PowerShell session." -ForegroundColor Red
        Write-Host "Install WSL 2, restore C:\Windows\System32 in PATH, or verify with: where.exe wsl" -ForegroundColor Red
        return 1
    }

    $wslArgs = @()
    $wslArgs += Get-CodexWslDistroArgs
    $wslArgs += @("-e", "bash", "--", $ScriptPath)
    $wslArgs += $Arguments

    & $wslExe @wslArgs
    return $LASTEXITCODE
}
