#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot

$prometheusUrl = if ($env:PROMETHEUS_URL) { $env:PROMETHEUS_URL } else { "http://host.docker.internal:9090" }
$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "-e",
    "PROMETHEUS_URL=$prometheusUrl"
)

if ($env:PROMETHEUS_USERNAME) {
    $dockerArgs += @("-e", "PROMETHEUS_USERNAME=$($env:PROMETHEUS_USERNAME)")
}
if ($env:PROMETHEUS_PASSWORD) {
    $dockerArgs += @("-e", "PROMETHEUS_PASSWORD=$($env:PROMETHEUS_PASSWORD)")
}
if ($env:PROMETHEUS_TOKEN) {
    $dockerArgs += @("-e", "PROMETHEUS_TOKEN=$($env:PROMETHEUS_TOKEN)")
}

$dockerArgs += "ghcr.io/pab1it0/prometheus-mcp-server"

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
