#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertFrom-BioetlNeo4jAuth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Auth
    )

    $separatorIndex = $Auth.IndexOf('/')
    if ($separatorIndex -le 0 -or $separatorIndex -eq ($Auth.Length - 1)) {
        throw "NEO4J_AUTH must use non-empty username/password format"
    }

    return [pscustomobject]@{
        Username = $Auth.Substring(0, $separatorIndex)
        Password = $Auth.Substring($separatorIndex + 1)
    }
}

function Normalize-BioetlRepoEnvAliases {
    # GitHub MCP expects GITHUB_PERSONAL_ACCESS_TOKEN; local .env often has GITHUB_TOKEN.
    if (-not $env:GITHUB_PERSONAL_ACCESS_TOKEN) {
        if ($env:GITHUB_TOKEN) {
            $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_TOKEN
        } elseif ($env:GITHUB_CDX_PERSONAL_ACCESS_TOKEN) {
            $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_CDX_PERSONAL_ACCESS_TOKEN
        } elseif ($env:GITHUB_ANY_PERSONAL_ADjCCESS_TOKEN) {
            # Historical typo key kept for local compat (do not introduce in new .env files).
            $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_ANY_PERSONAL_ADjCCESS_TOKEN
        }
    }
    if (-not $env:GITHUB_TOKEN -and $env:GITHUB_PERSONAL_ACCESS_TOKEN) {
        $env:GITHUB_TOKEN = $env:GITHUB_PERSONAL_ACCESS_TOKEN
    }

    if (-not $env:NEEDLE_API_KEY -and $env:NEEDLE_TOKEN) {
        $env:NEEDLE_API_KEY = $env:NEEDLE_TOKEN
    }

    if (-not $env:BRAVE_API_KEY) {
        if ($env:BRAVE_SEARCH_API_KEY) {
            $env:BRAVE_API_KEY = $env:BRAVE_SEARCH_API_KEY
        } elseif ($env:BRAVE_API_KEY1) {
            $env:BRAVE_API_KEY = $env:BRAVE_API_KEY1
        }
    }

    # Context7 optional key aliases
    if (-not $env:CONTEXT7_API_KEY) {
        if ($env:CONTEXT7_API_TOKEN) {
            $env:CONTEXT7_API_KEY = $env:CONTEXT7_API_TOKEN
        } elseif ($env:UPSTASH_CONTEXT7_API_KEY) {
            $env:CONTEXT7_API_KEY = $env:UPSTASH_CONTEXT7_API_KEY
        }
    }

    if (-not $env:HUB_PAT_TOKEN) {
        if ($env:DOCKERHUB_PAT) {
            $env:HUB_PAT_TOKEN = $env:DOCKERHUB_PAT
        } elseif ($env:DOCKERHUB_TOKEN) {
            $env:HUB_PAT_TOKEN = $env:DOCKERHUB_TOKEN
        } elseif ($env:DOCKERHUB_PAT_TOKEN) {
            $env:HUB_PAT_TOKEN = $env:DOCKERHUB_PAT_TOKEN
        } elseif ($env:DOCKER_API_KEY) {
            # Non-canonical alias used in some local .env files
            $env:HUB_PAT_TOKEN = $env:DOCKER_API_KEY
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

    # Neo4j auth pack → discrete username/password when needed.
    if ($env:NEO4J_AUTH) {
        $authParts = ConvertFrom-BioetlNeo4jAuth -Auth $env:NEO4J_AUTH
        if (-not $env:NEO4J_USERNAME) { $env:NEO4J_USERNAME = $authParts.Username }
        if (-not $env:NEO4J_PASSWORD) { $env:NEO4J_PASSWORD = $authParts.Password }
    }
    if (-not $env:NEO4J_URL -and $env:NEO4J_URI) {
        $env:NEO4J_URL = $env:NEO4J_URI
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
