# MCP memory server with branch/commit/worktree-scoped local persistence.
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..\..')).Path
. (Join-Path $scriptDir 'support\load_repo_env.ps1')
$env:BIOETL_SKIP_ENV_LOCAL = '1'
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $scriptDir 'support\token_validation.ps1')

Exit-McpValidateOnly -ServerName 'memory'

$memoryMode = if ([string]::IsNullOrWhiteSpace($env:BIOETL_AI_MEMORY_MODE)) {
    'off'
} else {
    $env:BIOETL_AI_MEMORY_MODE.ToLowerInvariant()
}
if ($memoryMode -notin @('read-write', 'readwrite', 'rw')) {
    if ($memoryMode -in @('off', 'disabled', 'read-only', 'readonly', 'ro')) {
        [Console]::Error.WriteLine(
            "Persistent MCP memory is disabled by BIOETL_AI_MEMORY_MODE=$memoryMode"
        )
        exit 78
    }
    [Console]::Error.WriteLine(
        'Invalid BIOETL_AI_MEMORY_MODE; expected off, read-only, or read-write'
    )
    exit 64
}

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot '.cache\npm-cache'
}
New-Item -ItemType Directory -Force -Path $env:NPM_CONFIG_CACHE | Out-Null
if ([string]::IsNullOrWhiteSpace($env:MEMORY_FILE_PATH)) {
    $env:PYTHONPATH = "$repoRoot\src" + $(if ($env:PYTHONPATH) { ";$env:PYTHONPATH" } else { '' })
    $env:MEMORY_FILE_PATH = (& python -m memory.mcp_scope `
        --repo-root $repoRoot `
        --seed (Join-Path $repoRoot 'docs\00-project\ai\memory\mcp-memory.json')).Trim()
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& npx -y '@modelcontextprotocol/server-memory@2026.1.26' @args
exit $LASTEXITCODE
