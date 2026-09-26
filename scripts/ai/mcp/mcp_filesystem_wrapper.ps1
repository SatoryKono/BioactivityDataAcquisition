#!/usr/bin/env pwsh
# MCP filesystem server: pin package and scope to repo root with a host-native
# absolute path. Avoids client-side expansion of portable "." into a foreign
# OS path under mixed Windows/WSL launches.
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
New-Item -ItemType Directory -Force -Path $env:NPM_CONFIG_CACHE | Out-Null

Exit-McpValidateOnly -ServerName "filesystem"

# Optional extra allowed roots after the repo root (advanced clients).
& npx -y "@modelcontextprotocol/server-filesystem@2026.1.14" $repoRoot @args
exit $LASTEXITCODE
