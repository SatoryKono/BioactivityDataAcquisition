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
    $branch = (& git -C $repoRoot branch --show-current 2>$null)
    if ([string]::IsNullOrWhiteSpace($branch)) { $branch = 'detached' }
    $branch = $branch -replace '[^A-Za-z0-9_.-]', '-'
    $commit = (& git -C $repoRoot rev-parse --verify HEAD 2>$null)
    if ([string]::IsNullOrWhiteSpace($commit)) { $commit = 'unknown' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($repoRoot)
        $worktreeId = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant().Substring(0, 16)
    } finally {
        $sha.Dispose()
    }
    $memoryDir = Join-Path $repoRoot ".cache\mcp-memory\$worktreeId\$branch\$commit"
    New-Item -ItemType Directory -Force -Path $memoryDir | Out-Null
    $env:MEMORY_FILE_PATH = Join-Path $memoryDir 'memory.json'
    if (-not (Test-Path -LiteralPath $env:MEMORY_FILE_PATH)) {
        $seed = Join-Path $repoRoot 'docs\00-project\ai\memory\mcp-memory.json'
        $temporary = "$($env:MEMORY_FILE_PATH).tmp.$PID"
        Copy-Item -LiteralPath $seed -Destination $temporary
        Move-Item -LiteralPath $temporary -Destination $env:MEMORY_FILE_PATH
    }
}
& npx -y '@modelcontextprotocol/server-memory@2026.1.26' @args
exit $LASTEXITCODE
