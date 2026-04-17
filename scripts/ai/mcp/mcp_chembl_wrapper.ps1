#!/usr/bin/env pwsh
param(
    [string[]]$ArgumentList
)

$scriptDir = $PSScriptRoot
$dockerCliResolverPath = Join-Path -Path $scriptDir -ChildPath "support\docker_cli_resolver.ps1"

# Import the Docker CLI resolver
. $dockerCliResolverPath

$dockerBin = Resolve-DockerBin
$arguments = @("mcp", "gateway", "run", "--servers", "chembl", "--transport", "stdio") + $ArgumentList

# Execute the command
& $dockerBin $arguments
