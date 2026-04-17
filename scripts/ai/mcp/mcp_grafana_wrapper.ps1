#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

$grafanaUrl = if ($env:GRAFANA_URL) { $env:GRAFANA_URL } else { "http://host.docker.internal:3000" }
$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "-e",
    "GRAFANA_URL=$grafanaUrl"
)

if ($env:GRAFANA_SERVICE_ACCOUNT_TOKEN) {
    $dockerArgs += @("-e", "GRAFANA_SERVICE_ACCOUNT_TOKEN=$($env:GRAFANA_SERVICE_ACCOUNT_TOKEN)")
}
if ($env:GRAFANA_USERNAME) {
    $dockerArgs += @("-e", "GRAFANA_USERNAME=$($env:GRAFANA_USERNAME)")
}
if ($env:GRAFANA_PASSWORD) {
    $dockerArgs += @("-e", "GRAFANA_PASSWORD=$($env:GRAFANA_PASSWORD)")
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
