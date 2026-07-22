#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

if (-not $env:NEO4J_URI) {
    $env:NEO4J_URI = "bolt://localhost:7687"
}

if (-not $env:NEO4J_USERNAME) {
    if ($env:NEO4J_AUTH_USERNAME) {
        $env:NEO4J_USERNAME = $env:NEO4J_AUTH_USERNAME
    } else {
        throw "NEO4J_USERNAME is required for Neo4j Cypher MCP"
    }
}
if (-not $env:NEO4J_PASSWORD) {
    if ($env:NEO4J_AUTH_PASSWORD) {
        $env:NEO4J_PASSWORD = $env:NEO4J_AUTH_PASSWORD
    } else {
        throw "NEO4J_PASSWORD is required for Neo4j Cypher MCP"
    }
}
if (-not $env:NEO4J_DATABASE) {
    $env:NEO4J_DATABASE = "neo4j"
}
if (-not $env:NEO4J_URL) {
    $env:NEO4J_URL = $env:NEO4J_URI
}
if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

Test-McpNeo4jCredentials -Purpose "Neo4j Cypher MCP"
Exit-McpValidateOnly -ServerName "neo4j-cypher"

# @daanrongen/neo4j-mcp requires bun on Windows and fails with:
#   '"bun"' is not recognized...
# Use the pinned Node-based @alanse/mcp-neo4j-server instead.
& npx -y "@alanse/mcp-neo4j-server@0.2.0" @args
exit $LASTEXITCODE
