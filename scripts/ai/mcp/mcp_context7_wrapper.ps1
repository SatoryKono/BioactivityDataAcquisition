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
    $env:NPM_CONFIG_CACHE = Join-Path ([System.IO.Path]::GetTempPath()) "bioetl-npm-cache"
}

# Optional higher rate limits: CONTEXT7_API_KEY from .env / shell.
# Warnings go to stderr only (see Write-McpTokenWarning) so MCP stdout stays pure JSON.
Test-McpOptionalToken `
    -Name "CONTEXT7_API_KEY" `
    -MinLength 8 `
    -Purpose "Context7 MCP (optional higher rate limits)"

Exit-McpValidateOnly -ServerName "context7"

# CONTEXT7_API_KEY is inherited by the child; never expose it in process argv.
# Do not remap stdout — MCP framing must pass through unmodified.
& npx -y "@upstash/context7-mcp@3.2.4"
exit $LASTEXITCODE
