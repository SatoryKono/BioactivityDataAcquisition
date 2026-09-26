#Requires -Version 5.1
<#
.SYNOPSIS
  Watchdog for BioETL shared MCP plane: restart down catalog servers.

.DESCRIPTION
  Runs health-shared, then start-shared for any DOWN daily (or listed) servers.
  Safe to schedule every 5–15 minutes. Does not touch bioetl/neo4j compose.
  Never increases thrash by starting neo4j-* unless -IncludeNeo4j.

.EXAMPLE
  .\scripts\ops\runtime\mcp\watchdog-shared.ps1
  .\scripts\ops\runtime\mcp\watchdog-shared.ps1 -Daily
  # Task Scheduler: powershell -NoProfile -File ...\watchdog-shared.ps1 -Daily
#>
[CmdletBinding()]
param(
    [switch]$Daily,
    [switch]$IncludeNeo4j,
    [string[]]$Servers = @(),
    [int]$SettleSeconds = 40,
    [int]$HealthTimeoutSec = 3
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

$healthScript = Join-Path $PSScriptRoot 'health-shared.ps1'
$startScript = Join-Path $PSScriptRoot 'start-shared.ps1'
$catalog = Get-Content (Join-Path $PSScriptRoot 'shared-servers.json') -Raw | ConvertFrom-Json
$logDir = Join-Path $Root 'logs\mcp-shared'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$names = @($catalog.servers.PSObject.Properties.Name)
if ($Daily -or ($Servers.Count -eq 0 -and -not $IncludeNeo4j)) {
    $names = @($names | Where-Object { $_ -notmatch '^neo4j-' })
}
if ($Servers.Count -gt 0) {
    $want = @($Servers | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $names = @($want)
}
if (-not $IncludeNeo4j) {
    $names = @($names | Where-Object { $_ -notmatch '^neo4j-' })
}

Write-Host "=== watchdog-shared $(Get-Date -Format o) servers=$($names -join ',') ==="

# Capture health without stopping on exit 1
$healthOut = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $healthScript `
    -Servers ($names -join ',') -TimeoutSec $HealthTimeoutSec -OverallTimeoutSec 60 2>&1
$healthOut | ForEach-Object { Write-Host $_ }

$down = @()
foreach ($line in $healthOut) {
    $s = [string]$line
    if ($s -match '^\[DOWN\]\s+(\S+)') {
        $down += $Matches[1]
    }
}

$report = [ordered]@{
    checked_at = (Get-Date).ToString('o')
    watched = $names
    down = $down
    restarted = @()
    ok = $true
}

if ($down.Count -eq 0) {
    Write-Host 'watchdog-shared: all watched servers up'
    $report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $logDir 'watchdog.json') -Encoding utf8
    exit 0
}

Write-Host "watchdog-shared: restarting $($down -join ', ')"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startScript `
    -Servers ($down -join ',') -SettleSeconds $SettleSeconds -MaxAttempts 2 -SkipPrewarm
$startExit = $LASTEXITCODE
$report.restarted = $down
$report.start_exit = $startExit

# Re-health
$health2 = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $healthScript `
    -Servers ($names -join ',') -TimeoutSec $HealthTimeoutSec -OverallTimeoutSec 60 2>&1
$health2 | ForEach-Object { Write-Host $_ }
$stillDown = @()
foreach ($line in $health2) {
    if ([string]$line -match '^\[DOWN\]\s+(\S+)') { $stillDown += $Matches[1] }
}
$report.still_down = $stillDown
$report.ok = ($stillDown.Count -eq 0)
$report | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $logDir 'watchdog.json') -Encoding utf8

if ($stillDown.Count -gt 0) {
    Write-Warning "watchdog-shared: still down: $($stillDown -join ', ')"
    exit 1
}
Write-Host 'watchdog-shared: recovered'
exit 0
