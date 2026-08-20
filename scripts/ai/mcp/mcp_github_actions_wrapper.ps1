#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

# Prefer a local checkout when present; otherwise use published npm package.
$localGithubActionsMcp = Join-Path $env:USERPROFILE "github-actions-mcp/dist/index.js"
$localGithubActionsMain = Join-Path $env:USERPROFILE "github-actions-mcp/dist/main.js"

Exit-McpValidateOnly -ServerName "github-actions"

if (Test-Path $localGithubActionsMcp) {
    & node $localGithubActionsMcp --stdio
    exit $LASTEXITCODE
}
if (Test-Path $localGithubActionsMain) {
    & node $localGithubActionsMain --stdio
    exit $LASTEXITCODE
}

# Published package: github-actions-mcp (bin: github-actions-mcp)
# (The old @modelcontextprotocol/server-github-actions package is 404.)
& npx -y "github-actions-mcp@1.0.1" --stdio
exit $LASTEXITCODE
