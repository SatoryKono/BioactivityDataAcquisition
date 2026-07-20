#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

# GitHub Actions MCP configuration
$localGithubActionsMcp = Join-Path $env:USERPROFILE "github-actions-mcp/dist/index.js"

if (Test-Path $localGithubActionsMcp) {
    & node $localGithubActionsMcp --stdio
} else {
    # Fallback to npx if local installation not found
    & npx -y @modelcontextprotocol/server-github-actions --stdio
}

exit $LASTEXITCODE