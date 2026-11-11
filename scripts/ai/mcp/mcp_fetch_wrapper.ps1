#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
Exit-McpValidateOnly -ServerName "fetch"
. (Join-Path $PSScriptRoot "support/run_owned_stdio.ps1")

$launcher = Resolve-OwnedMcpLauncherOrExit `
    -LauncherRelativePath "pc-agent/mcp-shared/public-fetch-v1/project-launcher.json" `
    -Policy "public-fetch-v1" `
    -OwnerPathPattern '^[A-Za-z]:[\\/].*[\\/]fetch-owner\.py$' `
    -MissingOwnerMessage "Fetch MCP requires the registered Windows owner."

$adapterArgs = '-I -S -B "' + $launcher.owner + '" client'
exit (Invoke-OwnedMcpStdio -Python $launcher.python -Arguments $adapterArgs)
