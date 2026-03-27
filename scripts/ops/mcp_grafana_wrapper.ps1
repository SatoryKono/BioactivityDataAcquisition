if (-not $env:NPM_CONFIG_CACHE) {
    $env:NPM_CONFIG_CACHE = Join-Path $env:TEMP "npm-cache"
}

if (-not $env:GRAFANA_URL) {
    $env:GRAFANA_URL = "http://localhost:3000"
}

if (-not $env:GRAFANA_SERVICE_ACCOUNT_TOKEN) {
    if (-not $env:GRAFANA_USERNAME) {
        $env:GRAFANA_USERNAME = "admin"
    }
    if (-not $env:GRAFANA_PASSWORD) {
        if ($env:GF_SECURITY_ADMIN_PASSWORD) {
            $env:GRAFANA_PASSWORD = $env:GF_SECURITY_ADMIN_PASSWORD
        } else {
            $env:GRAFANA_PASSWORD = "change_me"
        }
    }
}

& npx -y "mcp-grafana-npx@1.0.1"
exit $LASTEXITCODE
