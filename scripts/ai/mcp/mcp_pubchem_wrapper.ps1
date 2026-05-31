#!/usr/bin/env pwsh
param(
    [string[]]$ArgumentList
)

$scriptDir = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
$dockerCliResolverPath = Join-Path -Path $scriptDir -ChildPath "support\docker_cli_resolver.ps1"

# Import the Docker CLI resolver
. $dockerCliResolverPath
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue

$dockerBin = Resolve-DockerBin
$arguments = @("mcp", "gateway", "run", "--servers", "pubchem", "--transport", "stdio") + $ArgumentList

# Execute the command
& $dockerBin $arguments
