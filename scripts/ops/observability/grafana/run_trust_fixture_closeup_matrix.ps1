# Capture Trust validation close-ups for fixture states via local fixture server.
# Temporarily repoints Grafana "BioETL Ops HTTP" datasource to host fixture server.
# Restores original URL in finally. Does not commit datasource changes.

param(
  [string]$GrafanaUrl = "http://localhost:3000",
  [string]$FixtureHost = "127.0.0.1",
  [int]$FixturePort = 18080,
  [string]$OpsHttpFromGrafana = "http://host.docker.internal:18080",
  [string[]]$States = @("populated", "valid_empty_or_unknown", "backend_error", "service_unavailable", "empty_rows"),
  [string]$OutRoot = "reports/observability/grafana/visual-baseline-20260811/trust-closeups-by-state"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
Set-Location $repo

# Load .env without printing secrets
Get-Content .env -ErrorAction SilentlyContinue | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $k, $v = $_.Split('=', 2)
  if ($k -and $null -ne $v -and -not [string]::IsNullOrWhiteSpace($k)) {
    if (-not (Test-Path "Env:$k")) {
      Set-Item -Path "Env:$k" -Value $v.Trim('"').Trim("'")
    }
  }
}

$headers = @{}
if ($env:GRAFANA_SERVICE_ACCOUNT_TOKEN) {
  $headers["Authorization"] = "Bearer $($env:GRAFANA_SERVICE_ACCOUNT_TOKEN)"
} else {
  $user = if ($env:GRAFANA_USERNAME) { $env:GRAFANA_USERNAME } else { "admin" }
  $pass = if ($env:GF_SECURITY_ADMIN_PASSWORD) { $env:GF_SECURITY_ADMIN_PASSWORD } elseif ($env:GRAFANA_PASSWORD) { $env:GRAFANA_PASSWORD } else { "" }
  if (-not $pass) { throw "Missing Grafana credentials in env" }
  $pair = "{0}:{1}" -f $user, $pass
  $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
  $headers["Authorization"] = "Basic $b64"
}

function Get-OpsDs {
  $all = Invoke-RestMethod -Uri "$GrafanaUrl/api/datasources" -Headers $headers
  $ds = $all | Where-Object { $_.uid -eq "bioetl-ops-http" -or $_.name -eq "BioETL Ops HTTP" } | Select-Object -First 1
  if (-not $ds) { throw "BioETL Ops HTTP datasource not found" }
  return Invoke-RestMethod -Uri "$GrafanaUrl/api/datasources/$($ds.id)" -Headers $headers
}

function Set-OpsDsUrl([object]$ds, [string]$url) {
  $ds.url = $url
  if ($ds.jsonData -and $ds.jsonData.allowedHosts) {
    $ds.jsonData.allowedHosts = @($url)
  }
  $body = $ds | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Method Put -Uri "$GrafanaUrl/api/datasources/$($ds.id)" -Headers $headers -ContentType "application/json" -Body $body | Out-Null
}

$original = Get-OpsDs
$originalUrl = $original.url
Write-Host "Original Ops HTTP URL: $originalUrl"

# Start fixture server
$py = Join-Path $repo ".venv-win\Scripts\python.exe"
$serverOut = Join-Path $OutRoot "fixture-server.out"
$serverErr = Join-Path $OutRoot "fixture-server.err"
New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
$server = Start-Process -FilePath $py `
  -ArgumentList @(
    "scripts/ops/observability/grafana/serve_trust_validation_fixtures.py",
    "--host", $FixtureHost,
    "--port", "$FixturePort",
    "--default-state", "populated"
  ) `
  -WorkingDirectory $repo `
  -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $serverOut `
  -RedirectStandardError $serverErr

Start-Sleep -Seconds 1
try {
  Set-OpsDsUrl -ds $original -url $OpsHttpFromGrafana
  Write-Host "Ops HTTP temporarily -> $OpsHttpFromGrafana"

  $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $env:LOCALAPPDATA "ms-playwright"
  $matrix = @()
  foreach ($state in $States) {
    Write-Host "==== STATE $state ===="
    $active = Join-Path $repo "tests/fixtures/grafana/control_plane_validation/.active_state"
    Set-Content -Path $active -Value $state -NoNewline -Encoding utf8
    $stateDir = Join-Path $OutRoot $state
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    & node scripts/ops/observability/grafana/_capture_trust_closeups.cjs `
      --base-url $GrafanaUrl `
      --output-dir $stateDir `
      --width 1920 `
      --height 900 `
      --theme dark `
      --state $state `
      --pipeline chembl_activity `
      --run-type incremental `
      --run-id "00000000-0000-0000-0000-000000008576"
    if ($LASTEXITCODE -ne 0) { throw "closeup capture failed for state $state" }
    $matrix += @{
      state = $state
      dir = $stateDir
      png_count = @(Get-ChildItem $stateDir -Filter *.png).Count
    }
  }

  $summary = @{
    schema_version = 1
    issue = "#8576"
    related_issue = "#8578"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    ops_http_original = $originalUrl
    ops_http_capture = $OpsHttpFromGrafana
    fixture_server = "http://${FixtureHost}:${FixturePort}"
    states = $matrix
  } | ConvertTo-Json -Depth 6
  Set-Content -Path (Join-Path $OutRoot "MATRIX_SUMMARY.json") -Value $summary -Encoding utf8
  Write-Host "Wrote MATRIX_SUMMARY.json"
}
finally {
  try {
    $restore = Get-OpsDs
    Set-OpsDsUrl -ds $restore -url $originalUrl
    Write-Host "Restored Ops HTTP URL: $originalUrl"
  } catch {
    Write-Host "WARN: failed to restore datasource: $($_.Exception.Message)"
  }
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
  }
  $active = Join-Path $repo "tests/fixtures/grafana/control_plane_validation/.active_state"
  if (Test-Path $active) { Remove-Item $active -Force }
}
