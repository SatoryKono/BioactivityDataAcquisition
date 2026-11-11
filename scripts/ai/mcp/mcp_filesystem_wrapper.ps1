#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
Exit-McpValidateOnly -ServerName "filesystem"

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "Windows profile unavailable"
    }
    $localProfile = $env:LOCALAPPDATA
    if (-not $localProfile) {
        $localProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    }
    $path = Join-Path $localProfile "pc-agent/mcp-shared/filesystem-v1/project-launcher.json"
    $descriptor = Get-Item -LiteralPath $path
    if ($descriptor.PSIsContainer -or $descriptor.Length -gt 4096 -or
        ($descriptor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Invalid launcher descriptor"
    }
    $launcher = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($launcher.policy -ne "bioetl-source-readonly-v1" -or $launcher.profile -notmatch '\A[a-f0-9]{64}\z' -or
        $launcher.python -notmatch '^[A-Za-z]:[\\/].*[\\/]python\.exe$' -or
        $launcher.owner -notmatch '^[A-Za-z]:[\\/].*[\\/]filesystem-owner\.py$' -or
        -not (Test-Path -LiteralPath $launcher.python -PathType Leaf) -or
        -not (Test-Path -LiteralPath $launcher.owner -PathType Leaf)) {
        throw "Invalid launcher fields"
    }
} catch {
    [Console]::Error.WriteLine("Filesystem MCP requires the registered Windows owner.")
    exit 1
}

. (Join-Path $PSScriptRoot "support/run_owned_stdio.ps1")
$adapterArgs = '-I -S -B "' + $launcher.owner + '" --production client ' + $launcher.profile
exit (Invoke-OwnedMcpStdio -Python $launcher.python -Arguments $adapterArgs)
