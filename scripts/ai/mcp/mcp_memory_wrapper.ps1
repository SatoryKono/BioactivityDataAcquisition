# MCP memory server with branch/commit/worktree-scoped local persistence.
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..\..')).Path
$explicitMemoryMode = $null
if (Test-Path Env:BIOETL_AI_MEMORY_MODE) {
    $explicitMemoryMode = $env:BIOETL_AI_MEMORY_MODE
}
. (Join-Path $scriptDir 'support\load_repo_env.ps1')
$env:BIOETL_SKIP_ENV_LOCAL = '1'
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
if ($null -ne $explicitMemoryMode) {
    $env:BIOETL_AI_MEMORY_MODE = $explicitMemoryMode
}
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

$venvWinPython = Join-Path $repoRoot '.venv-win\Scripts\python.exe'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (Test-Path $venvWinPython) {
    $memoryPython = $venvWinPython
} elseif (Test-Path $venvPython) {
    $memoryPython = $venvPython
} else {
    $memoryPython = 'python'
}

$env:PYTHONPATH = "$repoRoot\src" + $(if ($env:PYTHONPATH) { ";$env:PYTHONPATH" } else { '' })
$scopeArgs = @()
if (-not [string]::IsNullOrWhiteSpace($env:MEMORY_FILE_PATH)) {
    $scopeArgs += @('--target', $env:MEMORY_FILE_PATH)
}
$seed = if ($env:MEMORY_SEED_PATH) { $env:MEMORY_SEED_PATH } else {
    Join-Path $repoRoot 'docs\00-project\ai\memory\mcp-memory.json'
}
$env:MEMORY_REPO_ROOT = $repoRoot
$scopeOutput = & $memoryPython -m memory.mcp_scope --repo-root $repoRoot --seed $seed @scopeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$env:MEMORY_FILE_PATH = ([string]$scopeOutput).Trim()
& $memoryPython -m memory.mcp_server @args
exit $LASTEXITCODE
