#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot

if (-not $env:SONARQUBE_TOKEN) {
    throw "SONARQUBE_TOKEN is required for sonarqube MCP."
}

if (-not $env:SONARQUBE_ORG -and -not $env:SONARQUBE_URL) {
    throw "Set SONARQUBE_ORG for SonarQube Cloud or SONARQUBE_URL for SonarQube Server."
}

$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "--init",
    "--pull=always",
    "-e",
    "SONARQUBE_TOKEN"
)

if ($env:SONARQUBE_ORG) {
    $dockerArgs += @("-e", "SONARQUBE_ORG")
}

if ($env:SONARQUBE_URL) {
    $dockerArgs += @("-e", "SONARQUBE_URL")
}

if ($env:TELEMETRY_DISABLED) {
    $dockerArgs += @("-e", "TELEMETRY_DISABLED")
}

$dockerArgs += "mcp/sonarqube"

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
