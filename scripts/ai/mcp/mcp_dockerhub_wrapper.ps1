#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot

if (-not $env:DOCKERHUB_USERNAME) {
    throw "DOCKERHUB_USERNAME is required for dockerhub MCP."
}
if (-not $env:HUB_PAT_TOKEN) {
    throw "HUB_PAT_TOKEN is required for dockerhub MCP."
}

$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "-e",
    "HUB_PAT_TOKEN=$($env:HUB_PAT_TOKEN)",
    "mcp/dockerhub",
    "--username",
    $env:DOCKERHUB_USERNAME
)

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
