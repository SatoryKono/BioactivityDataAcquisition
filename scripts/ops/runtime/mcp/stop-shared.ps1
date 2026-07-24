#Requires -Version 5.1
<#
.SYNOPSIS
  Stop BioETL shared MCP plane processes started by start-shared.ps1.

.DESCRIPTION
  Stops processes recorded in logs/mcp-shared/pids/*.pid and best-effort
  listeners on shared-servers.json ports that look like mcp-proxy.
  Never stops bioetl / bioetl-neo4j containers.

.EXAMPLE
  .\scripts\ops\runtime\mcp\stop-shared.ps1
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string[]]$Servers = @()
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

$catalogPath = Join-Path $PSScriptRoot 'shared-servers.json'
$catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json
$logDir = Join-Path $Root 'logs\mcp-shared'
$pidDir = Join-Path $logDir 'pids'

$allNames = @($catalog.servers.PSObject.Properties.Name)
$selected = if ($Servers.Count -gt 0) { $Servers } else { $allNames }
$stopped = 0

foreach ($name in $selected) {
    $pidFile = Join-Path $pidDir "$name.pid"
    if (Test-Path $pidFile) {
        $pidText = (Get-Content $pidFile -Raw).Trim()
        if ($pidText -match '^\d+$') {
            $pid = [int]$pidText
            if ($PSCmdlet.ShouldProcess("pid=$pid ($name)", 'Stop-Process tree')) {
                try {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                    & taskkill.exe /PID $pid /F /T 2>$null | Out-Null
                    Write-Host "Stopped $name pid=$pid"
                    $stopped++
                } catch {
                    Write-Warning "Failed to stop $name pid=$pid : $($_.Exception.Message)"
                }
            }
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

# Best-effort: kill remaining mcp-proxy listeners on catalog ports.
foreach ($name in $selected) {
    $entry = $catalog.servers.$name
    if (-not $entry) { continue }
    $port = [int]$entry.port
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            $opid = $c.OwningProcess
            if ($opid -le 4) { continue }
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$opid" -ErrorAction SilentlyContinue
            $cmd = [string]$proc.CommandLine
            if ($cmd -match 'mcp-proxy') {
                if ($PSCmdlet.ShouldProcess("pid=$opid port=$port", 'Stop mcp-proxy listener')) {
                    Stop-Process -Id $opid -Force -ErrorAction SilentlyContinue
                    & taskkill.exe /PID $opid /F /T 2>$null | Out-Null
                    Write-Host "Stopped mcp-proxy on port $port pid=$opid"
                    $stopped++
                }
            }
        }
    } catch {
        # Get-NetTCPConnection may be unavailable; ignore.
    }
}

Write-Host "stop-shared done (actions≈$stopped)."
exit 0
