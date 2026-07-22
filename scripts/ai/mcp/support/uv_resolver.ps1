#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Enable-BioetlUvxNetworkBypass {
    <#
    .SYNOPSIS
      Bypass a broken Windows system HTTP proxy for uv/uvx package downloads.

    .NOTES
      On this host, urllib/uv default to system proxy 176.99.11.77:8080 which
      times out for PyPI, while direct HTTPS works. NO_PROXY=* forces direct.
    #>
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
