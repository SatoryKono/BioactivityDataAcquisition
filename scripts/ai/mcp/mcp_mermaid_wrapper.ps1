#!/usr/bin/env pwsh
param(
    [ValidateSet("stdio", "streamable")]
    [string]$Transport = "stdio",
    [ValidateRange(1, 65535)]
    [int]$Port = 3033,
    [ValidateSet("/mcp")]
    [string]$Endpoint = "/mcp",
    [ValidateSet("127.0.0.1", "localhost")]
    [string]$BindHost = "127.0.0.1",
    [string[]]$ArgumentList
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$package = "mcp-mermaid@0.4.1"
$localAppData = [Environment]::GetFolderPath("LocalApplicationData")
if ([string]::IsNullOrWhiteSpace($localAppData)) {
    $localAppData = [System.IO.Path]::GetTempPath()
}
$cacheRoot = Join-Path $localAppData "bioetl-mcp"
if ([string]::IsNullOrWhiteSpace($env:NPM_CONFIG_CACHE) -or $env:NPM_CONFIG_CACHE.StartsWith("/")) {
    $env:NPM_CONFIG_CACHE = Join-Path $cacheRoot "npm-cache"
}
if (-not [string]::IsNullOrWhiteSpace($env:PLAYWRIGHT_BROWSERS_PATH) -and $env:PLAYWRIGHT_BROWSERS_PATH.StartsWith("/")) {
    Remove-Item Env:PLAYWRIGHT_BROWSERS_PATH
}

# Avoid upstream's sudo-oriented postinstall. Browser payload is user-local and
# the explicit install is idempotent after the first successful download.
$env:npm_config_ignore_scripts = "true"
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& npx -y "--package=$package" playwright install chromium *> $null
$installExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($installExitCode -ne 0) {
    throw "Failed to install Playwright Chromium for Mermaid MCP."
}

$arguments = @("-y", $package, "--transport", $Transport)
if ($Transport -eq "streamable") {
    $arguments += @("--host", $BindHost, "--port", [string]$Port, "--endpoint", $Endpoint)
}
if ($ArgumentList) {
    $arguments += $ArgumentList
}
& npx @arguments
exit $LASTEXITCODE
