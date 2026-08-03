#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
. (Join-Path $PSScriptRoot "support/uv_resolver.ps1")

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}
New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:UV_TOOL_DIR | Out-Null

Exit-McpValidateOnly -ServerName "fetch"

# Canonical transport: PyPI package via uvx (pinned in repo MCP policy).
# Do NOT use npm package "mcp-server-fetch" — registry copy 0.0.2 is a
# security-research canary, not a production MCP server.
$uvx = Resolve-BioetlUvxBin
if (-not (Test-BioetlUvxAvailable)) {
    Write-Error @"
fetch MCP requires uvx with the PyPI package mcp-server-fetch==2025.4.7.
Install uv (https://docs.astral.sh/uv/) so uvx is on PATH, or place uvx under
%LOCALAPPDATA%\Programs\Python\Python3*\Scripts\.
Do not use npm package mcp-server-fetch (canary / not production).
"@
    exit 1
}

Invoke-BioetlUvxWithScopedBypass `
    -UvxPath $uvx `
    -Package "mcp-server-fetch==2025.4.7" `
    -Command "mcp-server-fetch" `
    -UvxArguments @("--python", "3.13", "--with", "mcp<2")
exit $LASTEXITCODE
