#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "support/token_validation.ps1")
Exit-McpValidateOnly -ServerName "filesystem"
. (Join-Path $PSScriptRoot "support/run_owned_stdio.ps1")

$launcher = Resolve-OwnedMcpLauncherOrExit `
    -LauncherRelativePath "pc-agent/mcp-shared/filesystem-v1/project-launcher.json" `
    -Policy "bioetl-source-readonly-v1" `
    -OwnerPathPattern '^[A-Za-z]:[\\/].*[\\/]filesystem-owner\.py$' `
    -ProfilePattern '\A[a-f0-9]{64}\z' `
    -MissingOwnerMessage "Filesystem MCP requires the registered Windows owner."

$adapterArgs = '-I -S -B "' + $launcher.owner + '" --production client ' + $launcher.profile
exit (Invoke-OwnedMcpStdio -Python $launcher.python -Arguments $adapterArgs)
