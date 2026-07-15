# Compatibility wrapper. MCP servers are on-demand processes.

param(
    [ValidateSet('dev', 'prod')]
    [string]$Environment = 'dev'
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
if ($Environment -eq 'prod') {
    & "$ProjectDir\scripts\ops\docker-setup.ps1" start
    exit $LASTEXITCODE
}
codex mcp list
if ($LASTEXITCODE -ne 0) { throw "Unable to validate on-demand MCP registration." }
python "$ProjectDir\scripts\ai\mcp\protocol_smoke.py" --config "$ProjectDir\.mcp.json" --server memory --timeout 15
if ($LASTEXITCODE -ne 0) { throw "MCP initialize/tools-list smoke failed." }
Write-Host "On-demand MCP registration is available; no persistent MCP containers were started."
