#!/usr/bin/env pwsh
# Shared WSL helpers for Gemini PowerShell launchers.

$script:GeminiWslDistro = if ($env:BIOETL_WSL_DISTRO) {
    $env:BIOETL_WSL_DISTRO
} else {
    ""
}
$script:GeminiWslCommand = $null

function Get-GeminiWslCommand {
    if ($script:GeminiWslCommand -and (Test-Path $script:GeminiWslCommand)) {
        return $script:GeminiWslCommand
    }

    foreach ($commandName in @("wsl.exe", "wsl")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) {
            $script:GeminiWslCommand = $command.Source
            return $script:GeminiWslCommand
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
                $script:GeminiWslCommand = $candidate
                return $script:GeminiWslCommand
            }
        }
    }

    return $null
}

function Test-GeminiWslAvailable {
    return [bool](Get-GeminiWslCommand)
}

function Get-GeminiWslDistroArgs {
    if ($script:GeminiWslDistro) {
        return @("-d", $script:GeminiWslDistro)
    }
    return @()
}

function ConvertTo-GeminiWslPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowsPath
    )

    $resolved = ""
    $wslCommand = Get-GeminiWslCommand
    try {
        if ($wslCommand) {
            $wslArgs = @()
            $wslArgs += Get-GeminiWslDistroArgs
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

function Invoke-GeminiWslBashScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [string[]]$Arguments = @()
    )

    $wslCommand = Get-GeminiWslCommand
    if (-not $wslCommand) {
        Write-Host "ERROR: wsl.exe was not found from this PowerShell session." -ForegroundColor Red
        Write-Host "Install WSL 2, restore C:\Windows\System32 in PATH, or verify with: where.exe wsl" -ForegroundColor Red
        return 1
    }

    $wslArgs = @()
    $wslArgs += Get-GeminiWslDistroArgs
    $wslArgs += @("-e", "env", "-u", "GEMINI_CLI_IDE_WORKSPACE_PATH", "bash", "--", $ScriptPath)
    $wslArgs += $Arguments

    & $wslCommand @wslArgs
    return $LASTEXITCODE
}
