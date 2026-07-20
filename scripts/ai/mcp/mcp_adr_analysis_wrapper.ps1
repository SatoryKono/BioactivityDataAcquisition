#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

# ADR analysis configuration
$env:PROJECT_PATH = $repoRoot
$env:ADR_PATH = Join-Path $repoRoot "docs/02-architecture/decisions"

& npx -y @modelcontextprotocol/server-adr-analysis --stdio
exit $LASTEXITCODE