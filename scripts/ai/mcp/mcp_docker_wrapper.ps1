#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "support/docker_cli_resolver.ps1")

$DockerMcp = Resolve-DockerMcpGatewayBin
& $DockerMcp mcp gateway run --servers docker --transport stdio
exit $LASTEXITCODE
