#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $repoRoot "scripts/ops/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

if (-not $env:GITHUB_PERSONAL_ACCESS_TOKEN) {
    $token = ""
    try {
        $token = (& gh auth token 2>$null).Trim()
    } catch {
        $token = ""
    }

    if ($token) {
        $env:GITHUB_PERSONAL_ACCESS_TOKEN = $token
    }
}

& npx -y @modelcontextprotocol/server-github@2025.4.8 @args
exit $LASTEXITCODE
