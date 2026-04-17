#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $repoRoot "scripts/ops/support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = "/tmp/npm-cache"
}

& npx -y @modelcontextprotocol/server-github --stdio
exit $LASTEXITCODE
