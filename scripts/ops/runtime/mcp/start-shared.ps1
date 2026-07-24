#Requires -Version 5.1
<#
.SYNOPSIS
  Start BioETL shared MCP plane (stdio wrappers behind mcp-proxy Streamable HTTP).

.DESCRIPTION
  For each entry in shared-servers.json, if the port is free, start:
    npx -y mcp-proxy@PIN --port N --server stream -- <wrapper>
  Logs under logs/mcp-shared/; status in logs/mcp-shared/status.json.
  Does not touch bioetl / bioetl-neo4j compose stacks.

.EXAMPLE
  .\scripts\ops\runtime\mcp\start-shared.ps1
  .\scripts\ops\runtime\mcp\start-shared.ps1 -Servers adr-analysis,deja
#>
[CmdletBinding()]
param(
    [string[]]$Servers = @(),
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

$catalogPath = Join-Path $PSScriptRoot 'shared-servers.json'
if (-not (Test-Path $catalogPath)) {
    Write-Error "Missing catalog: $catalogPath"
    exit 1
}
$catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json
$proxyPkg = [string]$catalog.proxy_package
if ([string]::IsNullOrWhiteSpace($proxyPkg)) { $proxyPkg = 'mcp-proxy@6.5.4' }

$logDir = Join-Path $Root 'logs\mcp-shared'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$pidDir = Join-Path $logDir 'pids'
New-Item -ItemType Directory -Force -Path $pidDir | Out-Null

function Test-PortOpen {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(200)
        if ($ok -and $client.Connected) {
            $client.EndConnect($iar)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

$npx = Get-Command npx -ErrorAction SilentlyContinue
if (-not $npx) {
    Write-Error 'npx not found on PATH (required for mcp-proxy).'
    exit 1
}
# npx is usually a .cmd shim; Start-Process cannot use .cmd as -FilePath.
$comSpec = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($comSpec)) { $comSpec = 'cmd.exe' }

$status = [ordered]@{
    started_at = (Get-Date).ToString('o')
    proxy_package = $proxyPkg
    servers = @{}
}

$allNames = @($catalog.servers.PSObject.Properties.Name)
$selected = if ($Servers.Count -gt 0) { $Servers } else { $allNames }

foreach ($name in $selected) {
    $entry = $catalog.servers.$name
    if (-not $entry) {
        Write-Warning "Unknown shared server '$name'; skip"
        continue
    }
    $port = [int]$entry.port
    $wrapperBase = [string]$entry.wrapper
    $wrapper = Join-Path $Root "scripts\ai\mcp\${wrapperBase}.ps1"
    if (-not (Test-Path $wrapper)) {
        Write-Warning "Wrapper missing for $name : $wrapper"
        continue
    }

    if (Test-PortOpen -Port $port) {
        Write-Host "OK already listening 127.0.0.1:$port ($name)"
        $status.servers[$name] = @{ port = $port; state = 'already_up' }
        continue
    }

    $outLog = Join-Path $logDir "$name.out.log"
    $errLog = Join-Path $logDir "$name.err.log"
    $pidFile = Join-Path $pidDir "$name.pid"

    $inner = "npx -y $proxyPkg --port $port --server stream -- powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""
    $cmdLine = "/d /c $inner > `"$outLog`" 2> `"$errLog`""

    if ($WhatIf) {
        Write-Host "WhatIf: $comSpec $cmdLine"
        $status.servers[$name] = @{ port = $port; state = 'whatif' }
        continue
    }

    Write-Host "Starting shared MCP $name on 127.0.0.1:$port ..."
    $proc = Start-Process -FilePath $comSpec `
        -ArgumentList $cmdLine `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -PassThru

    $proc.Id | Set-Content -Path $pidFile -Encoding ascii
    # npx install + proxy boot can take several seconds on cold cache.
    Start-Sleep -Seconds 5
    $state = if (Test-PortOpen -Port $port) { 'started' } else { 'starting' }
    $status.servers[$name] = @{
        port = $port
        state = $state
        pid = $proc.Id
        url = "http://127.0.0.1:$port$($entry.path)"
    }
    Write-Host "  pid=$($proc.Id) state=$state"
}

$statusPath = Join-Path $logDir 'status.json'
($status | ConvertTo-Json -Depth 6) | Set-Content -Path $statusPath -Encoding utf8
Write-Host "Wrote $statusPath"
Write-Host 'Next: materialize --profile shared --transport-mode shared and restart AI clients.'
exit 0
