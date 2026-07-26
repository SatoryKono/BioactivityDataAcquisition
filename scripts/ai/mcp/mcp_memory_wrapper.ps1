# MCP memory server pinned to one repository-owned knowledge graph file.
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..\..')).Path
. (Join-Path $scriptDir 'support\load_repo_env.ps1')
$env:BIOETL_SKIP_ENV_LOCAL = '1'
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $scriptDir 'support\token_validation.ps1')

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot '.cache\npm-cache'
}
New-Item -ItemType Directory -Force -Path $env:NPM_CONFIG_CACHE | Out-Null
Exit-McpValidateOnly -ServerName 'memory'

if ([string]::IsNullOrWhiteSpace($env:MEMORY_FILE_PATH)) {
    $env:MEMORY_FILE_PATH = Join-Path $repoRoot 'docs\00-project\ai\memory\mcp-memory.json'
}
& npx -y '@modelcontextprotocol/server-memory@2026.1.26' @args
exit $LASTEXITCODE
