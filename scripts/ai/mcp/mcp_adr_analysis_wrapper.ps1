#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

# ADR analysis configuration (mcp-adr-analysis-server)
$env:PROJECT_PATH = $repoRoot
$env:ADR_PATH = Join-Path $repoRoot "docs/02-architecture/decisions"

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

Exit-McpValidateOnly -ServerName "adr-analysis"

# Published package: mcp-adr-analysis-server (bin: mcp-adr-analysis-server)
& npx -y mcp-adr-analysis-server --stdio
exit $LASTEXITCODE
