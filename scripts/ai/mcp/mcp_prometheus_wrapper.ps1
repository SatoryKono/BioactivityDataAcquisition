#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

$prometheusUrl = if ($env:PROMETHEUS_URL) { $env:PROMETHEUS_URL } else { "http://host.docker.internal:9090" }
Test-McpOptionalToken `
    -Name "PROMETHEUS_TOKEN" `
    -MinLength 20 `
    -Purpose "Prometheus MCP" `
    -AllowedPrefixes @("eyJ")
Exit-McpValidateOnly -ServerName "prometheus"

. (Join-Path $PSScriptRoot "support/mcp_docker_prune.ps1")
Remove-McpExitedContainers -ImageMatch "prometheus-mcp-server"

$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "--label", "bioetl.mcp=prometheus",
    "-e",
    "PROMETHEUS_URL=$prometheusUrl"
)

if ($env:PROMETHEUS_USERNAME) {
    $dockerArgs += @("-e", "PROMETHEUS_USERNAME")
}
if ($env:PROMETHEUS_PASSWORD) {
    $dockerArgs += @("-e", "PROMETHEUS_PASSWORD")
}
if ($env:PROMETHEUS_TOKEN) {
    $dockerArgs += @("-e", "PROMETHEUS_TOKEN")
}

$dockerArgs += "ghcr.io/pab1it0/prometheus-mcp-server"

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
