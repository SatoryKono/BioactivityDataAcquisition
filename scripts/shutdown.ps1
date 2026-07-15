# Compatibility wrapper. On-demand MCP processes have no Compose lifecycle.

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot

& "$ProjectDir\scripts\ops\docker-setup.ps1" stop
exit $LASTEXITCODE
