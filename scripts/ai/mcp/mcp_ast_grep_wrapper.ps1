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

# MCP server packages (not plain @ast-grep/cli). Try the primary package, then
# fall back to the mirror. Native command failures must not abort the fallback,
# so relax the error action around the npx invocations only.
$ErrorActionPreference = "Continue"
& npx -y "@notprolands/ast-grep-mcp" --stdio @args
if ($LASTEXITCODE -eq 0) { exit 0 }

& npx -y "@chousyn/ast-grep-mcp" --stdio @args
exit $LASTEXITCODE
