#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

# Auto-recall path configuration
$env:DEJA_AUTO_RECALL_PATH = Join-Path $repoRoot "AGENTS.md"

Exit-McpValidateOnly -ServerName "deja"

# Package: @vshulcz/deja-vu (bin: deja). MCP transport is the `mcp` subcommand
# (not `--stdio` — that flag is invalid for this CLI).
& npx -y "@vshulcz/deja-vu@0.17.0" mcp
exit $LASTEXITCODE
