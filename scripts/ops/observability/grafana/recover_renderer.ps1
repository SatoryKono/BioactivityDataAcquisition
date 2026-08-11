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
    GF_RENDERING_RENDERING_TIMEOUT (default 20s) so dead renderer does not
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

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    & docker compose -p $Project -f $ComposeFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($ComposeArgs -join ' ') failed exit=$LASTEXITCODE"
    }
}

Write-Host "=== Grafana renderer recovery (UI stays up) ==="
Write-Host "Project=$Project ComposeFile=$ComposeFile"

# 1) Snapshot state
Write-Host "`n[1/4] Current state"
docker ps -a --filter "name=renderer" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
docker ps -a --filter "name=bioetl-grafana" --format "table {{.Names}}\t{{.Status}}" 2>$null

# 2) Recreate renderer only (never force-recreate grafana here)
Write-Host "`n[2/4] Recreate renderer only"
Invoke-Compose @('up', '-d', '--force-recreate', '--no-deps', 'renderer')

# 3) Wait for health
Write-Host "`n[3/4] Wait for renderer health (max ${WaitSeconds}s)"
$deadline = (Get-Date).AddSeconds($WaitSeconds)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    $cid = docker compose -p $Project -f $ComposeFile ps -q renderer 2>$null
    if ($cid) {
        $status = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $cid 2>$null
        Write-Host "  renderer=$status"
        if ($status -eq 'healthy' -or $status -eq 'running') {
            # Prefer healthy; accept running if no health yet after start_period
            if ($status -eq 'healthy') {
                $healthy = $true
                break
            }
        }
        $oom = docker inspect --format '{{.State.OOMKilled}}' $cid 2>$null
        if ($oom -eq 'true') {
            Write-Warning "renderer OOMKilled — free host RAM before retry"
            break
        }
    }
    Start-Sleep -Seconds 3
}

# 4) Probes
Write-Host "`n[4/4] Probes"
try {
    $g = Invoke-WebRequest -Uri 'http://127.0.0.1:3000/api/health' -UseBasicParsing -TimeoutSec 5
    Write-Host "  Grafana /api/health -> $($g.StatusCode) (UI independent of renderer)"
} catch {
    Write-Warning "  Grafana UI probe failed: $($_.Exception.Message)"
}

if ($healthy) {
    Write-Host "`nOK: renderer recovered. Screenshots may proceed."
    exit 0
}

Write-Warning @"

Renderer not healthy within ${WaitSeconds}s.
Grafana UI should still work; screenshot/PDF calls fail-fast
(GF_RENDERING_RENDERING_TIMEOUT, default 20s).

Next:
  1) Check free RAM (need >= 4 GiB)
  2) docker logs <renderer-container> --tail 100
  3) Re-run this script after freeing memory
  4) Do NOT restart Grafana solely for renderer recovery
"@
exit 1
