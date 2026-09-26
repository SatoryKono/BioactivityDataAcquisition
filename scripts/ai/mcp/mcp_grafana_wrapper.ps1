#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

$grafanaUrl = if ($env:GRAFANA_URL) { $env:GRAFANA_URL } else { "http://host.docker.internal:3000" }
Test-McpOptionalToken `
    -Name "GRAFANA_SERVICE_ACCOUNT_TOKEN" `
    -MinLength 20 `
    -Purpose "Grafana MCP" `
    -AllowedPrefixes @("glsa_", "eyJ")
if ((-not $env:GRAFANA_SERVICE_ACCOUNT_TOKEN) -and (-not $env:GRAFANA_PASSWORD)) {
    Write-McpTokenWarning "Grafana MCP has neither GRAFANA_SERVICE_ACCOUNT_TOKEN nor username/password; server may start but Grafana calls can fail."
}
Exit-McpValidateOnly -ServerName "grafana"

. (Join-Path $PSScriptRoot "support/mcp_docker_prune.ps1")
Remove-McpExitedContainers -ImageMatch "mcp/grafana"

$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "--label", "bioetl.mcp=grafana",
    "-e",
    "GRAFANA_URL=$grafanaUrl"
)

if ($env:GRAFANA_SERVICE_ACCOUNT_TOKEN) {
    $dockerArgs += @("-e", "GRAFANA_SERVICE_ACCOUNT_TOKEN")
}
if ($env:GRAFANA_USERNAME) {
    $dockerArgs += @("-e", "GRAFANA_USERNAME=$($env:GRAFANA_USERNAME)")
}
if ($env:GRAFANA_PASSWORD) {
    $dockerArgs += @("-e", "GRAFANA_PASSWORD")
}
if ($env:GRAFANA_ORG_ID) {
    $dockerArgs += @("-e", "GRAFANA_ORG_ID=$($env:GRAFANA_ORG_ID)")
}

$dockerArgs += @("mcp/grafana", "-t", "stdio")
if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
