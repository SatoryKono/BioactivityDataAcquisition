#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Normalize-BioetlRepoEnvAliases {
    if (-not $env:GITHUB_PERSONAL_ACCESS_TOKEN -and $env:GITHUB_TOKEN) {
        $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_TOKEN
    }
    if (-not $env:GITHUB_TOKEN -and $env:GITHUB_PERSONAL_ACCESS_TOKEN) {
        $env:GITHUB_TOKEN = $env:GITHUB_PERSONAL_ACCESS_TOKEN
    }

    if (-not $env:SONARQUBE_TOKEN -and $env:SONAR_TOKEN) {
        $env:SONARQUBE_TOKEN = $env:SONAR_TOKEN
    }
    if (-not $env:SONAR_TOKEN -and $env:SONARQUBE_TOKEN) {
        $env:SONAR_TOKEN = $env:SONARQUBE_TOKEN
    }
    if (-not $env:SONARQUBE_ORG -and $env:SONAR_ORG) {
        $env:SONARQUBE_ORG = $env:SONAR_ORG
    }
    if (-not $env:SONARQUBE_URL -and $env:SONAR_HOST_URL) {
        $env:SONARQUBE_URL = $env:SONAR_HOST_URL
    }

    if (-not $env:NEEDLE_API_KEY -and $env:NEEDLE_TOKEN) {
        $env:NEEDLE_API_KEY = $env:NEEDLE_TOKEN
    }

    if (-not $env:BRAVE_API_KEY -and $env:BRAVE_SEARCH_API_KEY) {
        $env:BRAVE_API_KEY = $env:BRAVE_SEARCH_API_KEY
    }

    if (-not $env:HUB_PAT_TOKEN) {
        if ($env:DOCKERHUB_PAT) {
            $env:HUB_PAT_TOKEN = $env:DOCKERHUB_PAT
        } elseif ($env:DOCKERHUB_TOKEN) {
            $env:HUB_PAT_TOKEN = $env:DOCKERHUB_TOKEN
        }
    }
    if (-not $env:DOCKERHUB_USERNAME -and $env:DOCKER_USERNAME) {
        $env:DOCKERHUB_USERNAME = $env:DOCKER_USERNAME
    }

    if (-not $env:GRAFANA_SERVICE_ACCOUNT_TOKEN) {
        if ($env:GRAFANA_TOKEN) {
            $env:GRAFANA_SERVICE_ACCOUNT_TOKEN = $env:GRAFANA_TOKEN
        } elseif ($env:GRAFANA_API_KEY) {
            $env:GRAFANA_SERVICE_ACCOUNT_TOKEN = $env:GRAFANA_API_KEY
        }
    }
    if (-not $env:GRAFANA_USERNAME -and $env:GF_SECURITY_ADMIN_USER) {
        $env:GRAFANA_USERNAME = $env:GF_SECURITY_ADMIN_USER
    }
    if (-not $env:GRAFANA_PASSWORD -and $env:GF_SECURITY_ADMIN_PASSWORD) {
        $env:GRAFANA_PASSWORD = $env:GF_SECURITY_ADMIN_PASSWORD
    }
}

function Import-BioetlRepoEnv {
    param(
        [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
    )

    if ($env:BIOETL_REPO_ENV_LOADED -eq "1") {
        Normalize-BioetlRepoEnvAliases
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
        Normalize-BioetlRepoEnvAliases
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
    Normalize-BioetlRepoEnvAliases
}
