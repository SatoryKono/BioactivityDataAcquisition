#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}

$env:MUTMUT_PROJECT_PATH = $repoRoot

Exit-McpValidateOnly -ServerName "mutmut"

if (Get-Command uvx -ErrorAction SilentlyContinue) {
    & uvx --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    $hasUv = & python -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('uv') else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        & python -m uv tool run --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio
        exit $LASTEXITCODE
    }
}

Write-Error "mutmut MCP requires uvx (or python -m uv). Install uv: https://docs.astral.sh/uv/getting-started/installation/"
exit 1
