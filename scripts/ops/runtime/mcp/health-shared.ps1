#Requires -Version 5.1
<#
.SYNOPSIS
  Probe shared MCP plane endpoints (port + optional /ping).

.DESCRIPTION
  W1.3: per-server TCP/HTTP timeouts; always writes health.json; bounded wall clock.

.EXAMPLE
  .\scripts\ops\runtime\mcp\health-shared.ps1
  .\scripts\ops\runtime\mcp\health-shared.ps1 -TimeoutSec 2 -OverallTimeoutSec 30
#>
[CmdletBinding()]
param(
    [string[]]$Servers = @(),
    [int]$TimeoutSec = 3,
    [int]$OverallTimeoutSec = 45
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$catalog = Get-Content (Join-Path $PSScriptRoot 'shared-servers.json') -Raw | ConvertFrom-Json

$allNames = @($catalog.servers.PSObject.Properties.Name)
$selected = if ($Servers.Count -gt 0) {
    @($Servers | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
} else {
    $allNames
}
$failed = 0
$results = @()
$started = Get-Date
$deadline = $started.AddSeconds([Math]::Max(5, $OverallTimeoutSec))
$perTimeout = [Math]::Max(1, $TimeoutSec)

function Test-TcpPort {
    param([int]$Port, [int]$TimeoutMs)
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs)
        if (-not $ok) {
            return $false
        }
        if (-not $client.Connected) {
            return $false
        }
        try {
            $client.EndConnect($iar)
        } catch {
            Write-Verbose "TCP EndConnect failed on port ${Port}: $($_.Exception.Message)"
            return $false
        }
        return $true
    } catch {
        Write-Verbose "TCP probe failed on port ${Port}: $($_.Exception.Message)"
        return $false
    } finally {
        if ($null -ne $client) {
            try {
                $client.Close()
            } catch {
                Write-Verbose "TCP client close failed on port ${Port}: $($_.Exception.Message)"
            }
            try {
                $client.Dispose()
            } catch {
                Write-Verbose "TCP client dispose failed on port ${Port}: $($_.Exception.Message)"
            }
        }
    }
}

function Get-HttpPingResult {
    param([string]$Uri, [int]$TimeoutSec)
    try {
        # Prefer HttpWebRequest for hard timeout on older PowerShell.
        $req = [System.Net.HttpWebRequest]::Create($Uri)
        $req.Method = 'GET'
        $req.Proxy = $null
        $req.AllowAutoRedirect = $false
        if ($env:BIOETL_MCP_SHARED_API_KEY) {
            $req.Headers['X-API-Key'] = $env:BIOETL_MCP_SHARED_API_KEY
        }
        $req.Timeout = $TimeoutSec * 1000
        $req.ReadWriteTimeout = $TimeoutSec * 1000
        $req.KeepAlive = $false
        $resp = $null
        try {
            $resp = $req.GetResponse()
            return @{ Status = [int]$resp.StatusCode; Error = $null }
        } finally {
            if ($null -ne $resp) { $resp.Close() }
        }
    } catch [System.Net.WebException] {
        $response = $_.Exception.Response
        if ($null -ne $response) {
            try {
                return @{ Status = [int]$response.StatusCode; Error = $null }
            } finally {
                $response.Close()
            }
        }
        $failure = if ($_.Exception.Status -eq [System.Net.WebExceptionStatus]::Timeout) {
            'http_timeout'
        } else {
            'http_unreachable'
        }
        return @{ Status = $null; Error = $failure }
    }
}

foreach ($name in $selected) {
    if ((Get-Date) -gt $deadline) {
        Write-Warning "Overall timeout ($OverallTimeoutSec s) reached; remaining servers marked down"
        foreach ($rest in $selected) {
            if ($results | Where-Object { $_.Server -eq $rest }) { continue }
            $entryRest = $catalog.servers.$rest
            if (-not $entryRest) { continue }
            $failed++
            $results += [pscustomobject]@{
                Server = $rest
                Port = [int]$entryRest.port
                Url = "http://127.0.0.1:$([int]$entryRest.port)$([string]$entryRest.path)"
                PortOpen = $false
                PingOk = $false
                HttpStatus = $null
                ReadinessLevel = 'not_tested'
                Ok = $false
                Error = 'overall_timeout'
            }
            Write-Host ("[DOWN] {0} port=False ping=False (overall_timeout)" -f $rest)
        }
        break
    }

    $entry = $catalog.servers.$name
    if (-not $entry) {
        Write-Warning "Unknown server $name"
        $failed++
        $results += [pscustomobject]@{
            Server = $name
            Port = $null
            Url = $null
            PortOpen = $false
            PingOk = $false
            HttpStatus = $null
            ReadinessLevel = 'not_tested'
            Ok = $false
            Error = 'unknown'
        }
        continue
    }
    $port = [int]$entry.port
    $path = [string]$entry.path
    if ([string]::IsNullOrWhiteSpace($path)) { $path = '/mcp' }
    $base = "http://127.0.0.1:$port"
    $mcpUrl = "$base$path"
    $pingUrl = "$base/ping"
    $timeoutMs = $perTimeout * 1000
    $portUp = Test-TcpPort -Port $port -TimeoutMs $timeoutMs
    $pingOk = $false
    $httpStatus = $null
    $readiness = 'not_tested'
    $failure = 'tcp_unreachable'
    $nativeStreaming = [string]$entry.launch_mode -in @('windows_docker_streaming', 'windows_npx_streaming')
    if ($portUp) {
        if ($nativeStreaming) {
            $readiness = 'tcp'
            $failure = $null
        } else {
            $ping = Get-HttpPingResult -Uri $pingUrl -TimeoutSec $perTimeout
            $readiness = 'tcp'
            $httpStatus = $ping.Status
            $failure = $ping.Error
            if ($httpStatus -ge 200 -and $httpStatus -lt 300) {
                $pingOk = $true
                $readiness = 'http_ping'
            } elseif ($httpStatus -in @(401, 403)) {
                $failure = 'auth_rejected'
            } elseif ($null -ne $httpStatus) {
                $failure = 'http_error'
            }
        }
    }
    # Preserve the watchdog transport gate for native listeners.
    $ok = $portUp -and ($nativeStreaming -or $pingOk)
    if (-not $ok) { $failed++ }
    $line = [pscustomobject]@{
        Server = $name
        Port = $port
        Url = $mcpUrl
        PortOpen = $portUp
        PingOk = $pingOk
        HttpStatus = $httpStatus
        ReadinessLevel = $readiness
        Ok = $ok
        Error = $failure
    }
    $results += $line
    $mark = if ($ok) { 'OK' } elseif ($failure -eq 'auth_rejected') { 'AUTH' } else { 'DOWN' }
    Write-Host ("[{0}] {1} level={2} http={3} error={4} {5}" -f $mark, $name, $readiness, $httpStatus, $failure, $mcpUrl)
}

$logDir = Join-Path $Root 'logs\mcp-shared'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$healthPath = Join-Path $logDir 'health.json'
$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
@{
    checked_at = (Get-Date).ToString('o')
    failed = $failed
    timeout_sec = $perTimeout
    overall_timeout_sec = $OverallTimeoutSec
    elapsed_sec = $elapsed
    results = $results
} | ConvertTo-Json -Depth 6 | Set-Content -Path $healthPath -Encoding utf8

if ($failed -gt 0) {
    Write-Host "health-shared: $failed down in ${elapsed}s (see $healthPath)"
    exit 1
}
Write-Host "health-shared: all $($results.Count) up in ${elapsed}s"
exit 0
