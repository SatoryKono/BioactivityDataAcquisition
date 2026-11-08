#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Optional host route is resolved before env/cache/Docker side effects.
$mcpHostMarker = if ($env:PC_AGENT_MCP_ROUTES_FILE) { $env:PC_AGENT_MCP_ROUTES_FILE } else { Join-Path $HOME ".config/pc-agent/mcp-routes.json" }
if ($env:PC_AGENT_MCP_ROUTES_FILE -or (Get-Item -LiteralPath $mcpHostMarker -Force -ErrorAction SilentlyContinue)) {
    $mcpHostRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
    $mcpHostPathExt = $env:PATHEXT
    try {
        # Windows PowerShell needs PATHEXT even with an SDK-filtered environment.
        if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
            if ($env:PATHEXT -notmatch '(?i)(^|;)\.EXE(;|$)') {
                $env:PATHEXT = ".COM;.EXE;.BAT;.CMD" + $(if ($env:PATHEXT) { ";" + $env:PATHEXT })
            }
            $mcpHostNode = (Get-Command node.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
        } else {
            $mcpHostNode = (Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
        }
        & $mcpHostNode (Join-Path $PSScriptRoot "support/host_transport.mjs") --root $mcpHostRoot --server brave-search -- @args
        $mcpHostExit = $LASTEXITCODE
    } finally {
        $env:PATHEXT = $mcpHostPathExt
    }
    if ($mcpHostExit -ne 78) { exit $mcpHostExit }
}
Remove-Variable mcpHostMarker -ErrorAction SilentlyContinue

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

Test-McpRequiredToken -Name "BRAVE_API_KEY" -MinLength 31 -Purpose "Brave Search MCP"
Exit-McpValidateOnly -ServerName "brave-search"

. (Join-Path $PSScriptRoot "support/mcp_docker_prune.ps1")
# Reap exited orphans from previous stdio sessions (running peers stay).
Remove-McpExitedContainers -ImageMatch "mcp/brave-search"

$dockerArgs = @(
    "run",
    "--rm",
    "-i",
    "--label", "bioetl.mcp=brave-search",
    "-e",
    "BRAVE_API_KEY",
    "mcp/brave-search"
)

if ($args.Count -gt 0) {
    $dockerArgs += $args
}

& docker @dockerArgs
exit $LASTEXITCODE
