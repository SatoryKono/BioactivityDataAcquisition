#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $repoRoot ".cache/npm-cache"
}

# MCP server packages (not plain @ast-grep/cli). Try the primary package, then
# fall back to the mirror. Native command failures must not abort the fallback,
# so relax the error action around the npx invocations only.
$ErrorActionPreference = "Continue"
& npx -y "@notprolands/ast-grep-mcp" --stdio @args
if ($LASTEXITCODE -eq 0) { exit 0 }

& npx -y "@chousyn/ast-grep-mcp" --stdio @args
exit $LASTEXITCODE
