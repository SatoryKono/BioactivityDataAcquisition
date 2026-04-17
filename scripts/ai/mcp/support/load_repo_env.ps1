#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Import-BioetlRepoEnv {
    param(
        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
    )

    if ($env:BIOETL_REPO_ENV_LOADED -eq "1") {
        return
    }

    $envFile = if ($env:BIOETL_ENV_FILE) {
        $env:BIOETL_ENV_FILE
    } else {
        Join-Path $RepoRoot ".env"
    }
    $envLocalFile = if ($env:BIOETL_SKIP_ENV_LOCAL -eq "1") {
        $null
    } else {
        Join-Path $RepoRoot ".env.local"
    }

    if (-not (Test-Path $envFile) -and -not (Test-Path $envLocalFile)) {
        $env:BIOETL_REPO_ENV_LOADED = "1"
        return
    }

    $shellEnv = @{}
    Get-ChildItem Env: | ForEach-Object {
        $shellEnv[$_.Name] = $_.Value
    }

    $filesToLoad = @($envFile)
    if ($envLocalFile) {
        $filesToLoad += $envLocalFile
    }
    foreach ($file in $filesToLoad) {
        if (-not (Test-Path $file)) {
            continue
        }

        foreach ($rawLine in Get-Content -Path $file) {
            $line = $rawLine.Trim()
            if (-not $line -or $line.StartsWith("#") -or -not $rawLine.Contains("=")) {
                continue
            }

            $parts = $rawLine -split '=', 2
            if ($parts.Count -ne 2) {
                continue
            }

            $name = $parts[0].Trim()
            if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
                continue
            }

            if ($shellEnv.ContainsKey($name) -and -not [string]::IsNullOrEmpty($shellEnv[$name])) {
                continue
            }

            $value = $parts[1].Trim()
            if ($value.Length -ge 2 -and (
                    ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                    ($value.StartsWith("'") -and $value.EndsWith("'"))
                )) {
                $value = $value.Substring(1, $value.Length - 2)
            } else {
                $value = [regex]::Replace($value, '\s+#.*$', '').TrimEnd()
            }

            Set-Item -Path "Env:$name" -Value $value
        }
    }

    $env:BIOETL_REPO_ENV_LOADED = "1"
}
