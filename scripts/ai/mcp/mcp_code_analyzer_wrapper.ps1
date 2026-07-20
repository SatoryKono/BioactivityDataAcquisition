#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

# Code analyzer configuration
$env:PROJECT_PATH = $repoRoot

# Check if uvx is available
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    & uvx mcp-server-analyzer --stdio
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m uv mcp-server-analyzer --stdio
} else {
    Write-Error "Error: Neither uvx nor python with uv module found"
    exit 1
}

exit $LASTEXITCODE