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
    $env:NPM_CONFIG_CACHE = "/tmp/npm-cache"
}

if (-not $env:GITHUB_PERSONAL_ACCESS_TOKEN -and $env:GITHUB_TOKEN) {
    $env:GITHUB_PERSONAL_ACCESS_TOKEN = $env:GITHUB_TOKEN
}

Test-McpRequiredToken `
    -Name "GITHUB_PERSONAL_ACCESS_TOKEN" `
    -MinLength 20 `
    -Purpose "GitHub MCP" `
    -AllowedPrefixes @("ghp_", "github_pat_", "gho_", "ghu_", "ghs_", "ghr_")
Exit-McpValidateOnly -ServerName "github"

& npx -y @modelcontextprotocol/server-github --stdio
exit $LASTEXITCODE
