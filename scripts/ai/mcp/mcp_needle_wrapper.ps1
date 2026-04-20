#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = "/tmp/npm-cache"
}

if (-not $env:NEEDLE_API_KEY) {
    Write-Error "NEEDLE_API_KEY is not set; Needle MCP cannot authenticate."
}

& npx -y mcp-remote https://mcp.needle-ai.com/mcp --header "Authorization:Bearer $($env:NEEDLE_API_KEY)"
exit $LASTEXITCODE
