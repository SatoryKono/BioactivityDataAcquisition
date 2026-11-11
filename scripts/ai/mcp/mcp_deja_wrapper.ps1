#!/usr/bin/env pwsh
param([string]$DejaProfileName = $env:BIOETL_DEJA_PROFILE)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
Exit-McpValidateOnly -ServerName "deja"

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
        $DejaProfileName -cnotmatch '\A[a-z][a-z0-9-]{1,47}\z') {
        throw "Explicit Deja profile required"
    }
    $localProfile = $env:LOCALAPPDATA
    if (-not $localProfile) {
        $localProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    }
    $path = Join-Path $localProfile "pc-agent/mcp-shared/deja-v1/$DejaProfileName/project-launcher.json"
    $descriptor = Get-Item -LiteralPath $path
    if ($descriptor.PSIsContainer -or $descriptor.Length -gt 4096 -or
        ($descriptor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Invalid Deja launcher"
    }
    $launcher = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($launcher.policy -ne "deja-codex-export-v1" -or $launcher.profile -cne $DejaProfileName -or
        $launcher.python -notmatch '^[A-Za-z]:[\\/].*[\\/]python\.exe$' -or
        $launcher.owner -notmatch '^[A-Za-z]:[\\/].*[\\/]deja-owner\.py$' -or
        -not (Test-Path -LiteralPath $launcher.python -PathType Leaf) -or
        -not (Test-Path -LiteralPath $launcher.owner -PathType Leaf)) {
        throw "Invalid Deja launcher fields"
    }
} catch {
    [Console]::Error.WriteLine("Deja MCP requires an explicitly registered isolated profile.")
    exit 1
}

. (Join-Path $PSScriptRoot "support/run_owned_stdio.ps1")
$adapterArgs = '-I -S -B "' + $launcher.owner + '" client ' + $DejaProfileName
exit (Invoke-OwnedMcpStdio -Python $launcher.python -Arguments $adapterArgs)
