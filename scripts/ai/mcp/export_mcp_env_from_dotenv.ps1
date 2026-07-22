#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Load MCP-related secrets from repo .env into the current process and
  (optionally) User environment so Grok can expand ${VAR} in HTTP MCP headers.

.DESCRIPTION
  Stdio MCP wrappers already call Import-BioetlRepoEnv and read .env directly.
  HTTP MCP servers (e.g. ref) are started by Grok itself and only see process /
  User env vars. This script bridges that gap without writing secrets into
  config.toml.

  By default sets Process scope only. Pass -UserScope to also set User scope
  (requires restart of Grok / new terminals to fully apply).
#>
param(
    [string]$RepoRoot = "",
    [switch]$UserScope
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
}

. (Join-Path $PSScriptRoot "support/load_repo_env.ps1")
Import-BioetlRepoEnv -RepoRoot $RepoRoot
Normalize-BioetlRepoEnvAliases

$mcpKeys = @(
    "GITHUB_TOKEN",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "BRAVE_API_KEY",
    "REF_TOOL_API_KEY",
    "CONTEXT7_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "NEO4J_URI",
    "NEO4J_URL",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "NEO4J_AUTH",
    "NEO4J_DATABASE",
    "HUB_PAT_TOKEN",
    "DOCKER_API_KEY",
    "DOCKERHUB_USERNAME",
    "NEEDLE_API_KEY",
    "GRAFANA_SERVICE_ACCOUNT_TOKEN",
    "GRAFANA_URL",
    "PROMETHEUS_URL",
    "PROMETHEUS_TOKEN"
)

$exported = 0
foreach ($key in $mcpKeys) {
    $value = [Environment]::GetEnvironmentVariable($key, "Process")
    if ([string]::IsNullOrEmpty($value)) {
        continue
    }
    if ($UserScope) {
        $existingUser = [Environment]::GetEnvironmentVariable($key, "User")
        if ($existingUser -ne $value) {
            [Environment]::SetEnvironmentVariable($key, $value, "User")
        }
    }
    $exported += 1
    Write-Host ("[export] {0} set (len={1})" -f $key, $value.Length)
}

Write-Host ("[export] done: {0} MCP-related keys present in process env" -f $exported)
if ($UserScope) {
    Write-Host "[export] User-scope updates applied. Restart Grok (and new terminals) so HTTP MCP `${VAR}` expansion sees them."
} else {
    Write-Host "[export] Process-only. For Grok HTTP MCP (ref), re-run with -UserScope once, then restart Grok."
}
