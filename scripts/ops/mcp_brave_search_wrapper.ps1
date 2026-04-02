#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
. (Join-Path $PSScriptRoot "load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $repoRoot

if (-not $env:BRAVE_API_KEY) {
    throw "BRAVE_API_KEY is required for brave-search MCP."
}

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
