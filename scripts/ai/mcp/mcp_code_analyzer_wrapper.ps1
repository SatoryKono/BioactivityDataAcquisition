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
if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}

# Code analyzer configuration
$env:PROJECT_PATH = $repoRoot

Exit-McpValidateOnly -ServerName "code-analyzer"

# Prefer published npm MCP package (legacy mcp-server-analyzer / @modelcontextprotocol/server-analyzer are 404).
# Optional uvx path kept for environments that pin a Python analyzer tool.
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    try {
        & uvx mcp-server-analyzer --stdio
        if ($LASTEXITCODE -eq 0) { exit 0 }
    } catch {
        # fall through to npm package
    }
}

& npx -y "@darient/code-analyzer-mcp" --stdio
exit $LASTEXITCODE
