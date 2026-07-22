#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:BioetlProxyEnvironmentNames = @(
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy"
)

function Get-BioetlProxyEnvironmentSnapshot {
    $snapshot = [ordered]@{}
    foreach ($name in $script:BioetlProxyEnvironmentNames) {
        $snapshot[$name] = [Environment]::GetEnvironmentVariable(
            $name,
            [EnvironmentVariableTarget]::Process
        )
    }
    return $snapshot
}

function Restore-BioetlProxyEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Snapshot
    )

    foreach ($name in $script:BioetlProxyEnvironmentNames) {
        [Environment]::SetEnvironmentVariable(
            $name,
            $Snapshot[$name],
            [EnvironmentVariableTarget]::Process
        )
    }
}

function Enable-BioetlUvxNetworkBypass {
    <#
    .SYNOPSIS
      Bypass a broken Windows system HTTP proxy for uv/uvx package downloads.

    .NOTES
      Set BIOETL_UVX_DIRECT_NETWORK=1 to opt into direct traffic on hosts whose
      configured proxy is known to be broken. The default preserves egress.
    #>
    if ($env:BIOETL_UVX_DIRECT_NETWORK -ne "1") {
        return
    }
    $env:NO_PROXY = "*"
    $env:no_proxy = "*"
    foreach ($name in @(
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"
        )) {
        if (Test-Path "Env:$name") {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-BioetlUvxWithScopedBypass {
    <#
    .SYNOPSIS
      Resolve a uvx package without leaking the local proxy bypass to the MCP server.

    .DESCRIPTION
      uvx needs the direct-network workaround while it resolves the package. It
      launches a Python trampoline inside the resolved tool environment; the
      trampoline restores the original proxy variables before it starts the
      requested MCP command. The caller's process environment is restored in a
      finally block, including package-resolution failures.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$UvxPath,

        [Parameter(Mandatory = $true)]
        [string]$Package,

        [Parameter(Mandatory = $true)]
        [string]$Command,

        [string[]]$UvxArguments = @(),

        [string[]]$CommandArguments = @()
    )

    $snapshotVariable = "BIOETL_UVX_PROXY_ENV_B64"
    $snapshot = Get-BioetlProxyEnvironmentSnapshot
    $originalSnapshotValue = [Environment]::GetEnvironmentVariable(
        $snapshotVariable,
        [EnvironmentVariableTarget]::Process
    )
    $snapshotJson = $snapshot | ConvertTo-Json -Compress
    $snapshotBytes = [Text.Encoding]::UTF8.GetBytes($snapshotJson)
    $encodedSnapshot = [Convert]::ToBase64String($snapshotBytes)
    $trampoline = @'
import base64
import json
import os
import subprocess
import sys

snapshot_name = 'BIOETL_UVX_PROXY_ENV_B64'
snapshot = json.loads(base64.b64decode(os.environ.pop(snapshot_name)).decode('utf-8'))
for name, value in snapshot.items():
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
raise SystemExit(subprocess.call(sys.argv[1:]))
'@

    try {
        [Environment]::SetEnvironmentVariable(
            $snapshotVariable,
            $encodedSnapshot,
            [EnvironmentVariableTarget]::Process
        )
        Enable-BioetlUvxNetworkBypass

        $arguments = @()
        $arguments += $UvxArguments
        $arguments += @("--from", $Package, "python", "-c", $trampoline, $Command)
        $arguments += $CommandArguments
        & $UvxPath @arguments
    }
    finally {
        Restore-BioetlProxyEnvironment -Snapshot $snapshot
        [Environment]::SetEnvironmentVariable(
            $snapshotVariable,
            $originalSnapshotValue,
            [EnvironmentVariableTarget]::Process
        )
    }
}

function Resolve-BioetlUvxBin {
    <#
    .SYNOPSIS
      Locate uvx even when Scripts/ is not on PATH.
    #>
    $candidates = @()

    $fromPath = Get-Command uvx -ErrorAction SilentlyContinue
    if ($fromPath) {
        $candidates += $fromPath.Source
    }

    $fromUv = Get-Command uv -ErrorAction SilentlyContinue
    if ($fromUv) {
        $uvDir = Split-Path -Parent $fromUv.Source
        $candidates += (Join-Path $uvDir "uvx.exe")
        $candidates += (Join-Path $uvDir "uvx.cmd")
        $candidates += (Join-Path $uvDir "uvx")
    }

    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    $userProfile = $env:USERPROFILE
    $candidates += @(
        (Join-Path $localAppData "Programs\Python\Python313\Scripts\uvx.exe"),
        (Join-Path $localAppData "Programs\Python\Python312\Scripts\uvx.exe"),
        (Join-Path $localAppData "Programs\Python\Python311\Scripts\uvx.exe"),
        (Join-Path $userProfile ".local\bin\uvx.exe"),
        (Join-Path $userProfile ".cargo\bin\uvx.exe")
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    # Fall back to bare name (caller may still fail with a clear message).
    return "uvx"
}

function Test-BioetlUvxAvailable {
    $uvx = Resolve-BioetlUvxBin
    if ($uvx -eq "uvx") {
        $cmd = Get-Command uvx -ErrorAction SilentlyContinue
        return [bool]$cmd
    }
    return (Test-Path -LiteralPath $uvx)
}
