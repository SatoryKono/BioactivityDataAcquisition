#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

if (-not $env:NEO4J_URI) {
    $env:NEO4J_URI = "bolt://localhost:7687"
}

if ((-not $env:NEO4J_USERNAME) -or (-not $env:NEO4J_PASSWORD)) {
    if ($env:NEO4J_AUTH) {
        $authParts = $env:NEO4J_AUTH -split '/', 2
        if ($authParts.Count -eq 2) {
            if (-not $env:NEO4J_USERNAME) {
                $env:NEO4J_USERNAME = $authParts[0]
            }
            if (-not $env:NEO4J_PASSWORD) {
                $env:NEO4J_PASSWORD = $authParts[1]
            }
        }
    }
}

if (-not $env:NEO4J_USERNAME) {
    if ($env:NEO4J_AUTH_USERNAME) {
        $env:NEO4J_USERNAME = $env:NEO4J_AUTH_USERNAME
    } else {
        $env:NEO4J_USERNAME = "neo4j"
    }
}
if (-not $env:NEO4J_PASSWORD) {
    if ($env:NEO4J_AUTH_PASSWORD) {
        $env:NEO4J_PASSWORD = $env:NEO4J_AUTH_PASSWORD
    } else {
        $env:NEO4J_PASSWORD = "bioetl_secure_password"
    }
}
if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

$managedNodePrefixes = @(
    (Join-Path $repoRoot ".cache/tools/gemini-cli/npm-global"),
    (Join-Path $repoRoot ".cache/tools/codex-cli/npm-global")
)
foreach ($managedNodePrefix in $managedNodePrefixes) {
    $managedNode = Join-Path $managedNodePrefix "bin/node"
    if (Test-Path $managedNode) {
        $env:PATH = "$(Join-Path $managedNodePrefix "bin")$([IO.Path]::PathSeparator)$env:PATH"
        break
    }
}

if (-not $env:NEO4J_URL) {
    $env:NEO4J_URL = $env:NEO4J_URI
}

& npx -y @daanrongen/neo4j-mcp@1.1.4 @args
exit $LASTEXITCODE
