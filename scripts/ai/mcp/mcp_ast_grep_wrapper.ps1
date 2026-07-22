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

Exit-McpValidateOnly -ServerName "ast-grep"

# MCP server (not the plain @ast-grep/cli binary). Prefer the maintained npm MCP package.
# Fallback chain: @notprolands/ast-grep-mcp -> @chousyn/ast-grep-mcp
$candidates = @(
    "@notprolands/ast-grep-mcp",
    "@chousyn/ast-grep-mcp"
)
$lastError = $null
foreach ($pkg in $candidates) {
    try {
        & npx -y $pkg --stdio
        exit $LASTEXITCODE
    } catch {
        $lastError = $_
    }
}

if ($null -ne $lastError) {
    Write-Error "ast-grep MCP failed to start: $lastError"
}
exit 1
