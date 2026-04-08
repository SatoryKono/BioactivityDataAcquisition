#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
. (Join-Path $PSScriptRoot "load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot

if (-not $env:NEO4J_URI) {
    $env:NEO4J_URI = "bolt://localhost:7687"
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
if (-not $env:NEO4J_DATABASE) {
    $env:NEO4J_DATABASE = "neo4j"
}
if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = "/tmp/npm-cache"
}

& npx -y @knowall-ai/mcp-neo4j-agent-memory@0.2.5 @args
exit $LASTEXITCODE
