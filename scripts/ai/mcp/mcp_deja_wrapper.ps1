#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = ".cache/npm-cache"
}

# Auto-recall path configuration
$env:DEJA_AUTO_RECALL_PATH = Join-Path $repoRoot ".codex/AGENTS.md"

& npx -y @modelcontextprotocol/server-deja-vu@0.13.1 --stdio
exit $LASTEXITCODE