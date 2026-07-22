#!/usr/bin/env pwsh
# Docker Hub official MCP via Docker Desktop gateway (Windows-native).
# Secrets: HUB_PAT_TOKEN (or DOCKER_API_KEY / DOCKERHUB_PAT / DOCKERHUB_TOKEN aliases)
# Config: ~/.docker/mcp/config.yaml -> dockerhub.username
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
$env:BIOETL_SKIP_ENV_LOCAL = "1"
Import-BioetlRepoEnv -RepoRoot $repoRoot
Remove-Item Env:BIOETL_SKIP_ENV_LOCAL -ErrorAction SilentlyContinue
. (Join-Path $PSScriptRoot "support/docker_cli_resolver.ps1")
. (Join-Path $PSScriptRoot "support/token_validation.ps1")

# Docker Hub MCP catalog injects HUB_PAT_TOKEN. Prefer DOCKER_API_KEY when set
# (local .env alias used by the operator); otherwise fall back to canonical names.
if ($env:DOCKER_API_KEY) {
    $env:HUB_PAT_TOKEN = $env:DOCKER_API_KEY
}
elseif (-not $env:HUB_PAT_TOKEN) {
    if ($env:DOCKERHUB_PAT) {
        $env:HUB_PAT_TOKEN = $env:DOCKERHUB_PAT
    }
    elseif ($env:DOCKERHUB_TOKEN) {
        $env:HUB_PAT_TOKEN = $env:DOCKERHUB_TOKEN
    }
    elseif ($env:DOCKERHUB_PAT_TOKEN) {
        $env:HUB_PAT_TOKEN = $env:DOCKERHUB_PAT_TOKEN
    }
}

if (-not $env:DOCKERHUB_USERNAME -and $env:DOCKER_USERNAME) {
    $env:DOCKERHUB_USERNAME = $env:DOCKER_USERNAME
}

Test-McpRequiredToken `
    -Name "HUB_PAT_TOKEN" `
    -MinLength 20 `
    -Purpose "Docker Hub MCP" `
    -AllowedPrefixes @("dckr_pat_")
Exit-McpValidateOnly -ServerName "dockerhub"

# Materialize a short-lived secrets env for the gateway (does not print values).
$secretsDir = Join-Path ([System.IO.Path]::GetTempPath()) "bioetl-docker-mcp"
New-Item -ItemType Directory -Force -Path $secretsDir | Out-Null
$secretsFile = Join-Path $secretsDir ("hub-secrets-{0}.env" -f [guid]::NewGuid().ToString("N"))
# Docker MCP gateway .env secrets use secret names, not only runtime env names.
@(
    "dockerhub.pat_token=$($env:HUB_PAT_TOKEN)"
    "HUB_PAT_TOKEN=$($env:HUB_PAT_TOKEN)"
    $(if ($env:DOCKERHUB_USERNAME) { "DOCKERHUB_USERNAME=$($env:DOCKERHUB_USERNAME)" } else { $null })
) | Where-Object { $_ } | Set-Content -LiteralPath $secretsFile -Encoding utf8

# Ensure Desktop MCP config has username when we know it.
$configPath = Join-Path $env:USERPROFILE ".docker\mcp\config.yaml"
if ($env:DOCKERHUB_USERNAME -and (Test-Path -LiteralPath $configPath)) {
    $cfg = Get-Content -LiteralPath $configPath -Raw -ErrorAction SilentlyContinue
    if ($cfg -and ($cfg -notmatch '(?m)^dockerhub:\s*$') -and ($cfg -notmatch '(?m)^  username:')) {
        # leave as-is if structure unexpected; gateway also reads process env for some cases
    }
}

$DockerMcp = Resolve-DockerMcpGatewayBin
try {
    & $DockerMcp mcp gateway run `
        --servers dockerhub `
        --transport stdio `
        --secrets $secretsFile `
        --verify-signatures=false
    exit $LASTEXITCODE
}
finally {
    Remove-Item -LiteralPath $secretsFile -Force -ErrorAction SilentlyContinue
}
