#!/usr/bin/env pwsh
<#
.SYNOPSIS
Install Windows command-line shims for the BioETL Codex launchers.
#>

param(
    [string]$InstallDir = "",
    [switch]$DryRun,
    [switch]$SkipPathUpdate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-InstallDir {
    param([string]$RequestedInstallDir)

    if ($RequestedInstallDir) {
        return [System.IO.Path]::GetFullPath($RequestedInstallDir)
    }

    return [System.IO.Path]::Combine($env:USERPROFILE, "bin")
}

function New-ShimContent {
    param([string]$TargetPath)

    return @"
@echo off
call "$TargetPath" %*
exit /b %errorlevel%
"@
}

function New-PowerShellShimContent {
    param([string]$TargetPath)

    return @"
& "$TargetPath" @args
exit `$LASTEXITCODE
"@
}

function Write-Shim {
    param(
        [string]$Path,
        [string]$Content,
        [bool]$PreviewOnly
    )

    if ($PreviewOnly) {
        Write-Host "[dry-run] would write $Path"
        return
    }

    Set-Content -LiteralPath $Path -Value $Content -Encoding Ascii -NoNewline
    Write-Host "[ok] wrote $Path"
}

function Ensure-PathContainsInstallDir {
    param(
        [string]$TargetInstallDir,
        [bool]$PreviewOnly
    )

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @()
    if ($userPath) {
        $entries = $userPath.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries)
    }

    $alreadyPresent = $entries | Where-Object {
        $_.TrimEnd("\") -ieq $TargetInstallDir.TrimEnd("\")
    }

    if ($PreviewOnly) {
        if ($alreadyPresent) {
            Write-Host "[dry-run] would move $TargetInstallDir to the front of user PATH"
        }
        else {
            Write-Host "[dry-run] would prepend $TargetInstallDir to user PATH"
        }
        return
    }

    $filteredEntries = @($entries | Where-Object {
        $_.TrimEnd("\") -ine $TargetInstallDir.TrimEnd("\")
    })

    $updatedPath = if ($filteredEntries.Count -eq 0) {
        $TargetInstallDir
    }
    else {
        "$TargetInstallDir;$($filteredEntries -join ';')"
    }

    [Environment]::SetEnvironmentVariable("Path", $updatedPath, "User")
    if (-not ($env:Path.Split(";") | Where-Object {
        $_.TrimEnd("\") -ieq $TargetInstallDir.TrimEnd("\")
    })) {
        $env:Path = "$env:Path;$TargetInstallDir"
    }

    Write-Host "[ok] moved $TargetInstallDir to the front of user PATH"
}

$repoRoot = Get-RepoRoot
$resolvedInstallDir = Get-InstallDir -RequestedInstallDir $InstallDir

$shimMap = [ordered]@{
    "codex.cmd"       = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex.bat")
    "codex.ps1"       = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex.bat")
    "codex-exec.cmd"  = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex-exec.bat")
    "codex-exec.ps1"  = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex-exec.bat")
    "cx.cmd"          = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex.bat")
    "cx.ps1"          = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex.bat")
    "cxe.cmd"         = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex-exec.bat")
    "cxe.ps1"         = [System.IO.Path]::Combine($repoRoot, "scripts", "ops", "codex-exec.bat")
}

Write-Host "[codex-cmd] repo root: $repoRoot"
Write-Host "[codex-cmd] install dir: $resolvedInstallDir"

if ($DryRun) {
    Write-Host "[codex-cmd] dry-run mode enabled"
}

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $resolvedInstallDir -Force | Out-Null
}
else {
    Write-Host "[dry-run] would ensure directory $resolvedInstallDir exists"
}

foreach ($shimName in $shimMap.Keys) {
    $shimPath = [System.IO.Path]::Combine($resolvedInstallDir, $shimName)
    $shimContent = if ($shimName.EndsWith(".ps1")) {
        New-PowerShellShimContent -TargetPath $shimMap[$shimName]
    }
    else {
        New-ShimContent -TargetPath $shimMap[$shimName]
    }
    Write-Shim -Path $shimPath -Content $shimContent -PreviewOnly:$DryRun
}

if ($SkipPathUpdate) {
    Write-Host "[skip] PATH update disabled"
}
else {
    Ensure-PathContainsInstallDir -TargetInstallDir $resolvedInstallDir -PreviewOnly:$DryRun
}

Write-Host ""
Write-Host "Commands:"
Write-Host "  codex"
Write-Host "  codex-exec ""your prompt"""
Write-Host "  cx"
Write-Host "  cxe ""your prompt"""

if (-not $DryRun) {
    Write-Host ""
    Write-Host "Open a new cmd.exe / PowerShell session if the commands are not visible yet."
}
