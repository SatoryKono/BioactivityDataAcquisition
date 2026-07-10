#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

Test-McpRequiredToken -Name "BRAVE_API_KEY" -MinLength 32 -Purpose "Brave Search MCP"
Exit-McpValidateOnly -ServerName "brave-search"

$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "-e",
    "BRAVE_API_KEY=$($env:BRAVE_API_KEY)",
    "mcp/brave-search"
)

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
