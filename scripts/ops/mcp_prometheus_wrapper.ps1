#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
. (Join-Path $PSScriptRoot "load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot

$prometheusUrl = if ($env:PROMETHEUS_URL) { $env:PROMETHEUS_URL } else { "http://host.docker.internal:9090" }
$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "ghcr.io/pab1it0/prometheus-mcp-server",
    "--transport",
    "stdio",
    "--prometheus-url",
    $prometheusUrl
)

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
