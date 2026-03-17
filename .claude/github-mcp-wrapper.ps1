#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$token = ""
try {
    $token = (& gh auth token 2>$null).Trim()
} catch {
    $token = ""
}

if ($token) {
    $env:GITHUB_PERSONAL_ACCESS_TOKEN = $token
}

& npx -y @modelcontextprotocol/server-github@2025.4.8 @args
exit $LASTEXITCODE
