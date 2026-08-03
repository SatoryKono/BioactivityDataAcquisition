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
if (-not $env:ADR_PATH) {
    $env:ADR_PATH = Join-Path $repoRoot "docs/02-architecture/decisions"
}
# Default to prompt-only so the server works without OPENROUTER_API_KEY.
# Set EXECUTION_MODE=full + OPENROUTER_API_KEY for AI-executed analysis.
if (-not $env:EXECUTION_MODE) {
    $env:EXECUTION_MODE = "prompt-only"
}

# Prefer a local Windows temp cache: g-drive paths often hit EPERM on npx cleanup.
if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path ([System.IO.Path]::GetTempPath()) "bioetl-npm-cache"
}
# tree-sitter-* native modules frequently fail to build on Node 25 + older MSVC.
# The server supports reduced mode without them (README offline/native fallback).
# Match bash wrapper: only default to true when the operator has not set a value.
if (-not $env:npm_config_ignore_scripts) {
    $env:npm_config_ignore_scripts = "true"
}

Exit-McpValidateOnly -ServerName "adr-analysis"

# Package defaults to stdio MCP transport. Do not pass a bare "--stdio" flag —
# it is not a CLI option and can cause the process to exit immediately.
& npx -y mcp-adr-analysis-server
exit $LASTEXITCODE
