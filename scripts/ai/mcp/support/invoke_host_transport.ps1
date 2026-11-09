param([string]$RouteServer, [object[]]$RouteArgs)

$mcpHostExit = 78
# Optional host route is resolved before env/cache/Docker side effects.
$mcpHostMarker = if ($env:PC_AGENT_MCP_ROUTES_FILE) { $env:PC_AGENT_MCP_ROUTES_FILE } else { Join-Path $HOME ".config/pc-agent/mcp-routes.json" }
if ($env:PC_AGENT_MCP_ROUTES_FILE -or (Get-Item -LiteralPath $mcpHostMarker -Force -ErrorAction SilentlyContinue)) {
    $mcpHostRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
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
        & $mcpHostNode (Join-Path $PSScriptRoot "host_transport.mjs") --root $mcpHostRoot --server $RouteServer -- @RouteArgs
        $mcpHostExit = $LASTEXITCODE
    } finally {
        $env:PATHEXT = $mcpHostPathExt
    }
}
Remove-Variable mcpHostMarker -ErrorAction SilentlyContinue
