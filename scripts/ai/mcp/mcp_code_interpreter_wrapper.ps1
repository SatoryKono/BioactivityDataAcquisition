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
if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".cache/uv-cache"
}
if (-not $env:UV_TOOL_DIR) {
    $env:UV_TOOL_DIR = Join-Path $repoRoot ".cache/uv-tools"
}

Exit-McpValidateOnly -ServerName "mcp-code-interpreter"

# 1) Local Python module if installed
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $hasModule = & python -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('mcp_server_code_interpreter') else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        & python -m mcp_server_code_interpreter
        exit $LASTEXITCODE
    }
}

# 2) uvx when available
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    try {
        & uvx mcp-server-code-interpreter --stdio
        if ($LASTEXITCODE -eq 0) { exit 0 }
    } catch {
        # fall through
    }
}

# 3) npm fallback candidates (package names vary by publisher)
$npmCandidates = @(
    "mcp-server-code-interpreter",
    "@e2b/mcp-server"
)
foreach ($pkg in $npmCandidates) {
    try {
        & npx -y $pkg --stdio
        exit $LASTEXITCODE
    } catch {
        continue
    }
}

Write-Error @"
mcp-code-interpreter could not start.
Install one of:
  - pip/uv tool: mcp-server-code-interpreter
  - or ensure uvx is on PATH
  - or provide a local python module mcp_server_code_interpreter
"@
exit 1
