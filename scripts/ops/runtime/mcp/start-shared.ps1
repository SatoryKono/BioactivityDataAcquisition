#Requires -Version 5.1
<#
.SYNOPSIS
  Start BioETL shared MCP plane (stdio wrappers behind mcp-proxy Streamable HTTP).

.DESCRIPTION
  For each entry in shared-servers.json, if the port is free, start:
    npx -y mcp-proxy@PIN --port N --server stream -- <wrapper>
  Logs under logs/mcp-shared/; status in logs/mcp-shared/status.json.
  Does not touch bioetl / bioetl-neo4j compose stacks.

  W1.2 hardening:
  - Sequential start (one server at a time)
  - Pre-warm mcp-proxy package once
  - Shared NPM_CONFIG_CACHE under logs/mcp-shared/npm-cache
  - One retry on early process exit

.EXAMPLE
  .\scripts\ops\runtime\mcp\start-shared.ps1
  .\scripts\ops\runtime\mcp\start-shared.ps1 -Daily
  .\scripts\ops\runtime\mcp\start-shared.ps1 -Servers adr-analysis,deja

  Optional loopback auth (clients must send X-API-Key):
    $env:BIOETL_MCP_SHARED_API_KEY = '...'
    .\scripts\ops\runtime\mcp\start-shared.ps1 -Daily
#>
[CmdletBinding()]
param(
    [string[]]$Servers = @(),
    # Daily multi-client set: catalog minus neo4j-* (auth-dependent optional).
    [switch]$Daily,
    # Dry-run only (avoid reserved -WhatIf).
    [switch]$DryRun,
    # Host cold-start (npx + wrapper) often exceeds 12s; /ping is the success signal.
    [int]$SettleSeconds = 25,
    [int]$MaxAttempts = 2,
    [switch]$SkipPrewarm,
    # Bind host for mcp-proxy (default loopback only).
    [string]$BindHost = '127.0.0.1'
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
$nativeStreamingPorts = @(
    $catalog.servers.PSObject.Properties |
        Where-Object { [string]$_.Value.launch_mode -eq 'windows_docker_streaming' } |
        ForEach-Object { [int]$_.Value.port }
)
$proxyPkg = [string]$catalog.proxy_package
if ([string]::IsNullOrWhiteSpace($proxyPkg)) { $proxyPkg = 'mcp-proxy@6.5.4' }

$logDir = Join-Path $Root 'logs\mcp-shared'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$pidDir = Join-Path $logDir 'pids'
New-Item -ItemType Directory -Force -Path $pidDir | Out-Null
$npmCache = Join-Path $logDir 'npm-cache'
New-Item -ItemType Directory -Force -Path $npmCache | Out-Null
$launcherMutex = New-Object System.Threading.Mutex($false, 'Local\BioETL-MCP-Shared-Launcher')
if (-not $launcherMutex.WaitOne([TimeSpan]::FromMinutes(15))) {
    Write-Error 'Timed out waiting for the shared MCP launcher singleton lock.'
    exit 1
}

function Test-PortOpen {
    param([int]$Port, [int]$WaitMs = 300)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($WaitMs)
        if ($ok -and $client.Connected) {
            try { $client.EndConnect($iar) } catch {}
            $client.Close()
            return $true
        }
        try { $client.Close() } catch {}
        return $false
    } catch {
        return $false
    }
}

function Test-McpPing {
    param([int]$Port, [int]$TimeoutSec = 2)
    # Preferred ready gate: mcp-proxy /ping (not TCP-only).
    try {
        $uri = "http://127.0.0.1:$Port/ping"
        $req = [System.Net.HttpWebRequest]::Create($uri)
        $req.Method = 'GET'
        $req.Timeout = [Math]::Max(500, $TimeoutSec * 1000)
        $req.ReadWriteTimeout = $req.Timeout
        $resp = $req.GetResponse()
        try {
            $code = [int]$resp.StatusCode
            return ($code -ge 200 -and $code -lt 500)
        } finally {
            $resp.Close()
        }
    } catch {
        return $false
    }
}

function Test-McpReady {
    param([int]$Port)
    if ($nativeStreamingPorts -contains $Port) {
        return (Test-PortOpen -Port $Port)
    }
    return (Test-McpPing -Port $Port)
}

function Stop-McpProcessTree {
    param($Proc)
    if ($null -eq $Proc) { return }
    try {
        if ($Proc.HasExited) { return }
    } catch { return }
    try {
        & taskkill.exe /PID $Proc.Id /T /F 2>$null | Out-Null
    } catch {
        try { Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
}

function Wait-PortFreeOrReady {
    param([int]$Port, [int]$TimeoutSec = 12)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-McpReady -Port $Port) { return 'ready' }
        if (-not (Test-PortOpen -Port $Port)) { return 'free' }
        Start-Sleep -Milliseconds 250
    }
    if (Test-McpReady -Port $Port) { return 'ready' }
    if (-not (Test-PortOpen -Port $Port)) { return 'free' }
    return 'busy'
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Error 'npx not found on PATH (required for mcp-proxy).'
    exit 1
}
# npx is usually a .cmd shim; launch via cmd.exe with Start-Process redirects.
$comSpec = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($comSpec)) { $comSpec = 'cmd.exe' }

# Prefer dedicated cache so concurrent agents do not corrupt user-global _npx.
$env:NPM_CONFIG_CACHE = $npmCache
$env:BIOETL_MCP_SHARED = '1'

$statusPath = Join-Path $logDir 'status.json'
$status = [ordered]@{
    started_at = (Get-Date).ToString('o')
    proxy_package = $proxyPkg
    npm_cache = $npmCache
    servers = @{}
}
# Merge prior status so partial restarts (e.g. -Servers neo4j-*) do not wipe Daily entries.
if (Test-Path $statusPath) {
    try {
        $prev = Get-Content $statusPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($prev -and $prev.servers) {
            foreach ($prop in $prev.servers.PSObject.Properties) {
                $status.servers[$prop.Name] = @{
                    port  = $prop.Value.port
                    state = [string]$prop.Value.state
                    pid   = $prop.Value.pid
                    url   = [string]$prop.Value.url
                }
            }
        }
    } catch {
        Write-Warning "Could not merge prior status.json: $($_.Exception.Message)"
    }
}

function New-McpAttemptLogPaths {
    param(
        [string]$LogDir,
        [string]$Name,
        [int]$Attempt
    )
    # Always use unique stamp files so a still-open redirect handle from a prior
    # attempt/process cannot block Set-Content or Start-Process -RedirectStandard*.
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $suffix = if ($Attempt -le 1) { $stamp } else { "$stamp.a$Attempt" }
    return @{
        Out = (Join-Path $LogDir "$Name.out.$suffix.log")
        Err = (Join-Path $LogDir "$Name.err.$suffix.log")
    }
}

$allNames = @($catalog.servers.PSObject.Properties.Name)
# Prefer catalog priority then name for deterministic sequential start.
$ordered = @($allNames | Sort-Object {
    $e = $catalog.servers.$_
    if ($e.PSObject.Properties.Name -contains 'priority') { [int]$e.priority } else { 100 }
}, { $_ })

if ($Daily -and $Servers.Count -eq 0) {
    $Servers = @($ordered | Where-Object {
        $dailyEntry = $catalog.servers.$_
        -not ($dailyEntry.PSObject.Properties.Name -contains 'daily') -or [bool]$dailyEntry.daily
    })
    Write-Host "Daily profile: $($Servers -join ', ')"
}

# -File invocations often pass -Servers a,b,c as one string "a,b,c".
$selected = if ($Servers.Count -gt 0) {
    $want = @($Servers | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    @($ordered | Where-Object { $want -contains $_ }) + @($want | Where-Object { $ordered -notcontains $_ })
} else {
    $ordered
}

$apiKey = [string]$env:BIOETL_MCP_SHARED_API_KEY
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = ''
} else {
    Write-Host 'Auth: BIOETL_MCP_SHARED_API_KEY set (mcp-proxy --apiKey / clients need X-API-Key)'
}

if (-not $DryRun -and -not $SkipPrewarm) {
    Write-Host "Pre-warming $proxyPkg (cache=$npmCache) ..."
    $warmLog = Join-Path $logDir 'prewarm.err.log'
    $warmOut = Join-Path $logDir 'prewarm.out.log'
    $warmArgs = "/d /c npx -y $proxyPkg --help"
    try {
        $wp = Start-Process -FilePath $comSpec `
            -ArgumentList $warmArgs `
            -WorkingDirectory $Root `
            -WindowStyle Hidden `
            -RedirectStandardOutput $warmOut `
            -RedirectStandardError $warmLog `
            -PassThru `
            -Wait
        if ($wp.ExitCode -ne 0) {
            Write-Warning "Pre-warm exit=$($wp.ExitCode); continuing (see $warmLog)"
        } else {
            Write-Host "  pre-warm ok"
        }
    } catch {
        Write-Warning "Pre-warm failed: $($_.Exception.Message); continuing"
    }
}

$failed = 0
foreach ($name in $selected) {
    $entry = $catalog.servers.$name
    if (-not $entry) {
        Write-Warning "Unknown shared server '$name'; skip"
        $failed++
        continue
    }
    $port = [int]$entry.port
    $wrapperBase = [string]$entry.wrapper
    $wrapper = Join-Path $Root "scripts\ai\mcp\${wrapperBase}.ps1"
    if (-not (Test-Path $wrapper)) {
        Write-Warning "Wrapper missing for $name : $wrapper"
        $failed++
        continue
    }

    $mcpUrl = "http://127.0.0.1:$port$($entry.path)"
    if (Test-McpReady -Port $port) {
        Write-Host "OK already ready 127.0.0.1:$port ($name) /ping"
        $status.servers[$name] = @{
            port = $port
            state = 'already_up'
            url = $mcpUrl
        }
        continue
    }

    if (Test-PortOpen -Port $port) {
        Write-Warning "  port $port open but /ping not ready ($name); waiting before start..."
        $pre = Wait-PortFreeOrReady -Port $port -TimeoutSec ([Math]::Max(8, [int]($SettleSeconds / 2)))
        if ($pre -eq 'ready' -or (Test-McpReady -Port $port)) {
            Write-Host "OK became ready 127.0.0.1:$port ($name)"
            $status.servers[$name] = @{
                port = $port
                state = 'already_up'
                url = $mcpUrl
            }
            continue
        }
        if ($pre -ne 'free') {
            Write-Warning "  ${name}: port $port occupied without healthy /ping; skip"
            $status.servers[$name] = @{
                port = $port
                state = 'port_busy'
                url = $mcpUrl
            }
            $failed++
            continue
        }
    }

    $outLog = Join-Path $logDir "$name.out.log"
    $errLog = Join-Path $logDir "$name.err.log"
    $pidFile = Join-Path $pidDir "$name.pid"
    # cmd /c so .cmd npx works; RedirectStandard* (not shell >) so logs actually fill.
    # Always bind loopback; optional API key; longer connect timeout for docker wrappers.
    $connectionTimeoutMs = if ($catalog.PSObject.Properties.Name -contains 'connection_timeout_ms') {
        [int]$catalog.connection_timeout_ms
    } else { 180000 }
    $requestTimeoutMs = if ($catalog.PSObject.Properties.Name -contains 'request_timeout_ms') {
        [int]$catalog.request_timeout_ms
    } else { 300000 }
    $proxyFlags = "--host $BindHost --port $port --server stream --connectionTimeout $connectionTimeoutMs --requestTimeout $requestTimeoutMs"
    if (-not [string]::IsNullOrWhiteSpace($apiKey)) {
        # Quote key for cmd; avoid logging the secret.
        $escapedKey = $apiKey.Replace('"', '\"')
        $proxyFlags = "--apiKey `"$escapedKey`" $proxyFlags"
    }
    if ([string]$entry.launch_mode -eq 'windows_docker_streaming') {
        $cmdArgs = "/d /c docker mcp gateway run --servers $name --transport streaming --host $BindHost --port $port --allow-unauthenticated"
    } else {
        $cmdArgs = "/d /c set `"NPM_CONFIG_CACHE=$npmCache`"&& npx -y $proxyPkg $proxyFlags -- powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""
    }

    if ($DryRun) {
        Write-Host "DryRun: $comSpec $cmdArgs"
        $status.servers[$name] = @{ port = $port; state = 'whatif' }
        continue
    }

    $state = 'exited'
    $lastPid = $null
    $attempts = [Math]::Max(1, $MaxAttempts)
    # Docker/gateway wrappers need longer settle for image/gateway start.
    $serverSettle = if ($entry.PSObject.Properties.Name -contains 'readiness_timeout_sec') {
        [Math]::Max($SettleSeconds, [int]$entry.readiness_timeout_sec)
    } else { $SettleSeconds }
    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        # Never double-bind: healthy listener wins.
        if (Test-McpReady -Port $port) {
            $state = 'started'
            Write-Host "  $name ready on existing listener (attempt $attempt)"
            break
        }
        if (Test-PortOpen -Port $port) {
            Write-Warning "  $name port $port busy before attempt $attempt; waiting..."
            $gate = Wait-PortFreeOrReady -Port $port -TimeoutSec 8
            if ($gate -eq 'ready' -or (Test-McpReady -Port $port)) {
                $state = 'started'
                break
            }
            if ($gate -ne 'free') {
                $state = 'port_busy'
                Write-Warning "  $name cannot bind; port still busy"
                break
            }
        }

        $logPaths = New-McpAttemptLogPaths -LogDir $logDir -Name $name -Attempt $attempt
        $attemptOut = $logPaths.Out
        $attemptErr = $logPaths.Err
        # Touch empty files without truncating any live redirect handle.
        try {
            if (-not (Test-Path $attemptOut)) { New-Item -Path $attemptOut -ItemType File -Force | Out-Null }
            if (-not (Test-Path $attemptErr)) { New-Item -Path $attemptErr -ItemType File -Force | Out-Null }
        } catch {
            Write-Warning "  $name log prepare failed: $($_.Exception.Message); using paths anyway"
        }

        Write-Host "Starting shared MCP $name on 127.0.0.1:$port (attempt $attempt/$attempts, settle=${serverSettle}s, gate=/ping) ..."
        try {
            $proc = Start-Process -FilePath $comSpec `
                -ArgumentList $cmdArgs `
                -WorkingDirectory $Root `
                -WindowStyle Hidden `
                -RedirectStandardOutput $attemptOut `
                -RedirectStandardError $attemptErr `
                -PassThru
        } catch {
            Write-Warning "  $name Start-Process failed: $($_.Exception.Message)"
            $state = 'start_error'
            if ($attempt -lt $attempts) {
                Start-Sleep -Seconds 2
                continue
            }
            break
        }

        $lastPid = $proc.Id
        $proc.Id | Set-Content -Path $pidFile -Encoding ascii

        $deadline = (Get-Date).AddSeconds([Math]::Max(5, $serverSettle))
        $state = 'starting'
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 500
            if (Test-McpReady -Port $port) {
                $state = 'started'
                break
            }
            if ($proc.HasExited) {
                if (Test-McpReady -Port $port) {
                    $state = 'started'
                } else {
                    $state = 'exited'
                }
                break
            }
        }
        if ($state -eq 'starting') {
            if (Test-McpReady -Port $port) {
                $state = 'started'
            } else {
                $state = 'timeout'
            }
        }
        if ($state -eq 'started') {
            # Best-effort canonical names for operators (ignore lock races).
            try { Copy-Item $attemptOut $outLog -Force -ErrorAction SilentlyContinue } catch {}
            try { Copy-Item $attemptErr $errLog -Force -ErrorAction SilentlyContinue } catch {}
            break
        }
        # Failed attempt: kill process tree, wait free/ready, then retry (no double-bind).
        Write-Warning "  $name attempt $attempt failed (state=$state); stopping tree pid=$($proc.Id)"
        Stop-McpProcessTree -Proc $proc
        if (Test-McpReady -Port $port) {
            $state = 'started'
            break
        }
        $null = Wait-PortFreeOrReady -Port $port -TimeoutSec 10
        if ($attempt -lt $attempts) {
            Write-Warning "  $name retrying after cleanup"
            Start-Sleep -Seconds 2
        }
    }

    $status.servers[$name] = @{
        port = $port
        state = $state
        pid = $lastPid
        url = $mcpUrl
    }
    Write-Host "  pid=$lastPid state=$state"
    if ($state -ne 'started' -and $state -ne 'already_up') {
        Write-Warning "  $name failed (state=$state); see $errLog"
        $failed++
    }
}

$statusTempPath = "$statusPath.tmp"
($status | ConvertTo-Json -Depth 6) | Set-Content -Path $statusTempPath -Encoding utf8
Move-Item -Path $statusTempPath -Destination $statusPath -Force
Write-Host "Wrote $statusPath"
Write-Host 'Next: materialize --profile shared --transport-mode shared and restart AI clients.'
$launcherMutex.ReleaseMutex()
$launcherMutex.Dispose()
if ($failed -gt 0) {
    Write-Warning "start-shared: $failed server(s) failed to start"
    exit 1
}
exit 0
