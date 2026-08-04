#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:BioetlProxyEnvironmentNames = @(
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy"
)

function Get-BioetlProxyEnvironmentSnapshot {
    # Suppress enumeration so callers receive one case-sensitive map
    # (PowerShell otherwise unwraps single-collection returns).
    # Proxy variables are case-sensitive on POSIX. A normal PowerShell
    # hashtable is case-insensitive and would let a missing ``https_proxy``
    # overwrite a populated ``HTTPS_PROXY`` entry.
    $snapshot = [System.Collections.Generic.Dictionary[string, object]]::new(
        [System.StringComparer]::Ordinal
    )
    foreach ($name in $script:BioetlProxyEnvironmentNames) {
        $snapshot[$name] = [Environment]::GetEnvironmentVariable(
            $name,
            [EnvironmentVariableTarget]::Process
        )
    }
    Write-Output -NoEnumerate $snapshot
}

function ConvertTo-BioetlCaseSensitiveEnvironmentMap {
    param(
        [Parameter(Mandatory = $true)]
        $Snapshot
    )

    # Normalize to a dictionary whether callers pass Hashtable, OrderedDictionary,
    # or a PSCustomObject-wrapped map from PowerShell pipeline unwrapping.
    $map = [System.Collections.Generic.Dictionary[string, object]]::new(
        [System.StringComparer]::Ordinal
    )
    if ($Snapshot -is [System.Collections.IDictionary]) {
        foreach ($key in @($Snapshot.Keys)) {
            $map[[string]$key] = $Snapshot[$key]
        }
    }
    elseif ($null -ne $Snapshot) {
        foreach ($prop in $Snapshot.PSObject.Properties) {
            $map[[string]$prop.Name] = $prop.Value
        }
    }
    Write-Output -NoEnumerate $map
}

function Remove-BioetlProcessEnvironmentVariable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    [Environment]::SetEnvironmentVariable(
        $Name,
        $null,
        [EnvironmentVariableTarget]::Process
    )
    Remove-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
}

function Set-BioetlProcessEnvironmentVariable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    Set-Item -LiteralPath "Env:$Name" -Value $Value
    [Environment]::SetEnvironmentVariable(
        $Name,
        $Value,
        [EnvironmentVariableTarget]::Process
    )
}

function Restore-BioetlProxyEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        $Snapshot
    )

    $map = ConvertTo-BioetlCaseSensitiveEnvironmentMap -Snapshot $Snapshot

    # POSIX PowerShell Env provider conflates upper/lowercase proxy names.
    # Restore populated values FIRST so deleting an empty case alias cannot
    # erase its populated peer before we write it back (CI-C1-008 / #7520).
    foreach ($name in $script:BioetlProxyEnvironmentNames) {
        if (-not $map.ContainsKey($name)) {
            continue
        }
        $value = $map[$name]
        if ($null -ne $value -and $value -ne "") {
            Set-BioetlProcessEnvironmentVariable -Name $name -Value ([string]$value)
        }
    }

    foreach ($name in $script:BioetlProxyEnvironmentNames) {
        $value = $null
        if ($map.ContainsKey($name)) {
            $value = $map[$name]
        }
        if ($null -ne $value -and $value -ne "") {
            continue
        }
        # Skip removal when a case-variant sibling still holds a restored value.
        $siblingHasValue = $false
        $nameLower = $name.ToLowerInvariant()
        foreach ($other in $script:BioetlProxyEnvironmentNames) {
            if ($other -ceq $name) {
                continue
            }
            if ($other.ToLowerInvariant() -ne $nameLower) {
                continue
            }
            if (
                $map.ContainsKey($other) -and
                $null -ne $map[$other] -and
                $map[$other] -ne ""
            ) {
                $siblingHasValue = $true
                break
            }
        }
        if (-not $siblingHasValue) {
            Remove-BioetlProcessEnvironmentVariable -Name $name
        }
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
    foreach ($name in @("NO_PROXY", "no_proxy")) {
        Set-BioetlProcessEnvironmentVariable -Name $name -Value "*"
    }
    foreach ($name in @(
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"
        )) {
        Remove-BioetlProcessEnvironmentVariable -Name $name
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

    # Prefer explicit PATH probes first so test fakes (uvx.ps1) and non-Windows
    # pwsh path separators are honored before host-wide installs.
    $pathSeparator = [IO.Path]::PathSeparator
    $pathEntries = @()
    if (-not [string]::IsNullOrWhiteSpace($env:PATH)) {
        $pathEntries += $env:PATH.Split(
            [char[]]@($pathSeparator, ';', ':'),
            [StringSplitOptions]::RemoveEmptyEntries
        )
    }
    foreach ($entry in $pathEntries) {
        foreach ($name in @("uvx.exe", "uvx.cmd", "uvx.ps1", "uvx")) {
            try {
                $candidates += [System.IO.Path]::Combine($entry.Trim(), $name)
            }
            catch {
                Write-Verbose "Skipping unusable PATH entry '${entry}': $($_.Exception.Message)"
            }
        }
    }

    $candidates += Get-BioetlUvxCommandCandidates
    $candidates += Get-BioetlUvxInstallCandidates

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    # Fall back to bare name (caller may still fail with a clear message).
    return "uvx"
}

function Get-BioetlUvxCommandCandidates {
    $candidates = @()
    $fromPath = Get-Command uvx -ErrorAction SilentlyContinue
    if ($fromPath -and $fromPath.Source) {
        $candidates += $fromPath.Source
    }

    $fromUv = Get-Command uv -ErrorAction SilentlyContinue
    if ($fromUv -and $fromUv.Source) {
        $uvDir = Split-Path -Parent $fromUv.Source
        if (-not [string]::IsNullOrWhiteSpace($uvDir)) {
            foreach ($name in @("uvx.exe", "uvx.cmd", "uvx")) {
                try {
                    $candidates += [System.IO.Path]::Combine($uvDir, $name)
                } catch {
                    Write-Verbose "Skipping unusable uv sibling path: $($_.Exception.Message)"
                }
            }
        }
    }
    return ,$candidates
}

function Test-BioetlWindowsRuntime {
    if ($PSVersionTable.PSEdition -eq "Desktop") {
        return $true
    }
    if (Get-Variable -Name IsWindows -ErrorAction SilentlyContinue) {
        return [bool]$IsWindows
    }
    return ($env:OS -like "*Windows*")
}

function Add-BioetlPathCandidates {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IList]$Candidates,
        [Parameter(Mandatory = $true)]
        [string]$BasePath,
        [Parameter(Mandatory = $true)]
        [string[]]$RelativePaths,
        [Parameter(Mandatory = $true)]
        [string]$SkipLabel
    )
    if ([string]::IsNullOrWhiteSpace($BasePath)) {
        return
    }
    foreach ($rel in $RelativePaths) {
        try {
            $Candidates.Add([System.IO.Path]::Combine($BasePath, $rel)) | Out-Null
        } catch {
            Write-Verbose "Skipping ${SkipLabel} uvx candidate '${rel}': $($_.Exception.Message)"
        }
    }
}

function Get-BioetlWindowsUvxInstallCandidates {
    $candidates = [System.Collections.Generic.List[string]]::new()
    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    if (-not [string]::IsNullOrWhiteSpace($localAppData)) {
        foreach ($py in @("Python313", "Python312", "Python311")) {
            try {
                $candidates.Add([System.IO.Path]::Combine(
                    $localAppData,
                    "Programs",
                    "Python",
                    $py,
                    "Scripts",
                    "uvx.exe"
                )) | Out-Null
            } catch {
                Write-Verbose "Skipping LocalAppData uvx candidate for ${py}: $($_.Exception.Message)"
            }
        }
    }
    Add-BioetlPathCandidates `
        -Candidates $candidates `
        -BasePath ($env:USERPROFILE) `
        -RelativePaths @(".local\bin\uvx.exe", ".cargo\bin\uvx.exe") `
        -SkipLabel "user-profile"
    return ,@($candidates)
}

function Get-BioetlUnixUvxInstallCandidates {
    $candidates = [System.Collections.Generic.List[string]]::new()
    Add-BioetlPathCandidates `
        -Candidates $candidates `
        -BasePath ($env:HOME) `
        -RelativePaths @(".local/bin/uvx", ".cargo/bin/uvx") `
        -SkipLabel "home"
    return ,@($candidates)
}

function Get-BioetlUvxInstallCandidates {
    if (Test-BioetlWindowsRuntime) {
        return ,(Get-BioetlWindowsUvxInstallCandidates)
    }
    return ,(Get-BioetlUnixUvxInstallCandidates)
}

function Test-BioetlUvxAvailable {
    $uvx = Resolve-BioetlUvxBin
    if ($uvx -eq "uvx") {
        $cmd = Get-Command uvx -ErrorAction SilentlyContinue
        return [bool]$cmd
    }
    return (Test-Path -LiteralPath $uvx)
}
