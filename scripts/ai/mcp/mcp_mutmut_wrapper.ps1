#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
. (Join-Path $PSScriptRoot "support/uv_resolver.ps1")

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}
New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:UV_TOOL_DIR | Out-Null

$env:MUTMUT_PROJECT_PATH = $repoRoot

Exit-McpValidateOnly -ServerName "mutmut"

$uvx = Resolve-BioetlUvxBin
if (-not (Test-BioetlUvxAvailable)) {
    Write-Error @"
mutmut MCP requires uvx.
Install uv (https://docs.astral.sh/uv/) so uvx is on PATH, or place uvx under
%LOCALAPPDATA%\Programs\Python\Python3*\Scripts\.
"@
    exit 1
}

Enable-BioetlUvxNetworkBypass
& $uvx --from "git+https://github.com/wdm0006/mutmut-mcp@1e3b47ccaaa31f4c651d8e424b90d392d1c1ed90" mutmut-mcp --stdio
exit $LASTEXITCODE
