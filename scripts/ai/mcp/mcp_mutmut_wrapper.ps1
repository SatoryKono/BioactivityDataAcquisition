#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

# Mutmut MCP configuration
$env:MUTMUT_PROJECT_PATH = $repoRoot

# Check if uvx is available
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    & uvx --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m uv --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio
} else {
    Write-Error "Error: Neither uvx nor python with uv module found"
    exit 1
}

exit $LASTEXITCODE