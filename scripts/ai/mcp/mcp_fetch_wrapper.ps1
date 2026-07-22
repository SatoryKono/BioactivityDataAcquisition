#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}
if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

Exit-McpValidateOnly -ServerName "fetch"

# Prefer uvx with the pinned PyPI package used by repo .mcp.json.
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    & uvx --python 3.13 --from "mcp-server-fetch==2025.4.7" mcp-server-fetch
    exit $LASTEXITCODE
}

# Fallback: npm package (version stream differs from PyPI pin).
& npx -y mcp-server-fetch --stdio
exit $LASTEXITCODE
