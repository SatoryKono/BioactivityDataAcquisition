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
bash "$ProjectDir/scripts/ai/mcp/check.sh"
if ($LASTEXITCODE -ne 0) { throw "Unable to validate on-demand MCP registration." }
Write-Host "On-demand MCP registration is available; no persistent MCP containers were started."
