#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
if ($env:GITHUB_PERSONAL_ACCESS_TOKEN) {
    $env:BIOETL_GITHUB_TOKEN_SOURCE = "GITHUB_PERSONAL_ACCESS_TOKEN"
} elseif ($env:GITHUB_TOKEN) {
    $env:BIOETL_GITHUB_TOKEN_SOURCE = "GITHUB_TOKEN alias"
}
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
. (Join-Path $PSScriptRoot "support/github_mcp_server.ps1")

Resolve-BioetlGithubMcpToken
Test-McpRequiredToken `
    -Name "GITHUB_PERSONAL_ACCESS_TOKEN" `
    -MinLength 20 `
    -Purpose "GitHub MCP" `
    -AllowedPrefixes @("ghp_", "github_pat_", "gho_", "ghu_", "ghs_", "ghr_")
Set-BioetlGithubMcpPolicyEnv
Exit-McpValidateOnly -ServerName "github"

$githubMcpBin = Resolve-BioetlGithubMcpServerBin
$stdioArgs = Get-BioetlGithubMcpStdioArgs
& $githubMcpBin @stdioArgs
exit $LASTEXITCODE
