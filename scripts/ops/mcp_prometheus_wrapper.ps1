if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $env:TEMP "npm-cache"
}

if (-not $env:PROMETHEUS_URL) {
    $env:PROMETHEUS_URL = "http://localhost:9090"
}

& npx -y "prometheus-mcp@1.1.3" stdio
exit $LASTEXITCODE
