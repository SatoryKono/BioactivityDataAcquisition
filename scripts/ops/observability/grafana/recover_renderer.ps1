#Requires -Version 5.1
<#
.SYNOPSIS
  Recover the optional Grafana image renderer without restarting Grafana UI.

.DESCRIPTION
  Strategy when screenshots hang or renderer is OOMKilled:
    1) Do NOT restart Grafana (UI must stay up; rendering is best-effort).
    2) Recreate only the renderer service with a short health wait.
    3) Probe renderer /healthz (or healthcheck) and Grafana /api/health.

  Pair with compose fail-fast:
    GF_RENDERING_RENDERING_TIMEOUT (default 60s) so dead renderer does not
    block Grafana workers indefinitely.

.EXAMPLE
  .\scripts\ops\observability\grafana\recover_renderer.ps1
  .\scripts\ops\observability\grafana\recover_renderer.ps1 -WaitSeconds 90
#>
[CmdletBinding()]
param(
    [int]$WaitSeconds = 90,
    [string]$ComposeFile = 'docker-compose.monitoring.yml',
    [string]$Project = 'bioetl-monitoring'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $RepoRoot

# Prefer Python SSOT (same path as runtime_manager recover-renderer).
$py = $null
if (Test-Path '.\.venv-win\Scripts\python.exe') {
    $py = (Resolve-Path '.\.venv-win\Scripts\python.exe').Path
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $py = (Get-Command python).Source
}
if ($py) {
    $prev = $env:PYTHONPATH
    $env:PYTHONPATH = if ($prev) { "$RepoRoot;$prev" } else { $RepoRoot }
    try {
        & $py scripts/ops/observability/grafana/recover_renderer.py `
            --project $Project `
            --compose-file $ComposeFile `
            --wait $WaitSeconds
        exit $LASTEXITCODE
    } finally {
        if ($null -eq $prev) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
        else { $env:PYTHONPATH = $prev }
    }
}

# Fallback without Python: compose recreate only.
Write-Host "=== Grafana renderer recovery (UI stays up; python SSOT unavailable) ==="
& docker compose -p $Project -f $ComposeFile up -d --force-recreate --no-deps renderer
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
    $cid = docker compose -p $Project -f $ComposeFile ps -q renderer 2>$null
    if ($cid) {
        $status = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $cid 2>$null
        Write-Host "  renderer=$status"
        if ($status -eq 'healthy') { Write-Host 'OK'; exit 0 }
    }
    Start-Sleep -Seconds 3
}
Write-Warning "renderer not healthy within ${WaitSeconds}s; do NOT restart Grafana for renderer"
exit 1
