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
        & $mcpHostNode (Join-Path $PSScriptRoot "support/host_transport.mjs") --root $mcpHostRoot --server context7 -- @args
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

if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path ([System.IO.Path]::GetTempPath()) "bioetl-npm-cache"
}

# Optional higher rate limits: CONTEXT7_API_KEY from .env / shell.
# Warnings go to stderr only (see Write-McpTokenWarning) so MCP stdout stays pure JSON.
Test-McpOptionalToken `
    -Name "CONTEXT7_API_KEY" `
    -MinLength 8 `
    -Purpose "Context7 MCP (optional higher rate limits)"

Exit-McpValidateOnly -ServerName "context7"

# CONTEXT7_API_KEY is inherited by the child; never expose it in process argv.
# Do not remap stdout — MCP framing must pass through unmodified.
& npx -y "@upstash/context7-mcp@3.2.4"
exit $LASTEXITCODE
