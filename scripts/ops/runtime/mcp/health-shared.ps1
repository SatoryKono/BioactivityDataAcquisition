#Requires -Version 5.1
<#
.SYNOPSIS
  Probe shared MCP plane endpoints (port + optional /ping).

.EXAMPLE
  .\scripts\ops\runtime\mcp\health-shared.ps1
#>
[CmdletBinding()]
param(
    [string[]]$Servers = @(),
    [int]$TimeoutSec = 3
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$catalog = Get-Content (Join-Path $PSScriptRoot 'shared-servers.json') -Raw | ConvertFrom-Json

$allNames = @($catalog.servers.PSObject.Properties.Name)
$selected = if ($Servers.Count -gt 0) { $Servers } else { $allNames }
$failed = 0
$results = @()

foreach ($name in $selected) {
    $entry = $catalog.servers.$name
    if (-not $entry) {
        Write-Warning "Unknown server $name"
        $failed++
        continue
    }
    $port = [int]$entry.port
    $path = [string]$entry.path
    if ([string]::IsNullOrWhiteSpace($path)) { $path = '/mcp' }
    $base = "http://127.0.0.1:$port"
    $mcpUrl = "$base$path"
    $pingUrl = "$base/ping"
    $portUp = $false
    $pingOk = $false
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect('127.0.0.1', $port, $null, $null)
        $portUp = $iar.AsyncWaitHandle.WaitOne([Math]::Max(200, $TimeoutSec * 1000)) -and $tcp.Connected
        if ($portUp) { $tcp.EndConnect($iar) }
        $tcp.Close()
    } catch {
        $portUp = $false
    }
    if ($portUp) {
        try {
            $resp = Invoke-WebRequest -Uri $pingUrl -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
            $pingOk = ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
        } catch {
            # /ping optional; port open still counts as partial health
            $pingOk = $false
        }
    }
    $ok = $portUp
    if (-not $ok) { $failed++ }
    $line = [pscustomobject]@{
        Server = $name
        Port = $port
        Url = $mcpUrl
        PortOpen = $portUp
        PingOk = $pingOk
        Ok = $ok
    }
    $results += $line
    $mark = if ($ok) { 'OK' } else { 'DOWN' }
    Write-Host ("[{0}] {1} port={2} ping={3} {4}" -f $mark, $name, $portUp, $pingOk, $mcpUrl)
}

$logDir = Join-Path $Root 'logs\mcp-shared'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$healthPath = Join-Path $logDir 'health.json'
@{
    checked_at = (Get-Date).ToString('o')
    failed = $failed
    results = $results
} | ConvertTo-Json -Depth 6 | Set-Content -Path $healthPath -Encoding utf8

if ($failed -gt 0) {
    Write-Host "health-shared: $failed down (see $healthPath)"
    exit 1
}
Write-Host "health-shared: all $($results.Count) up"
exit 0
