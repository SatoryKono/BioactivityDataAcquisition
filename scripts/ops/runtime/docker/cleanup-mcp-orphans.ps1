#Requires -Version 5.1
<#
.SYNOPSIS
  Stop/remove orphan Docker MCP Toolkit containers (not BioETL stacks).

.DESCRIPTION
  Stdio MCP clients (Grok, Cursor, docker mcp gateway wrappers) each spawn
  containers with random names and labels docker-mcp=true / images mcp/*.
  When sessions reconnect without tearing down children, duplicates pile up
  inside the WSL VM and thrash Docker Desktop on 32 GiB hosts.

  This script removes those orphans only. It never touches:
    bioetl, bioetl-neo4j, any container whose name starts with bioetl-
    (includes future bioetl-mcp-* shared plane), or label bioetl.mcp.shared=true.

.EXAMPLE
  .\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1
  .\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$IncludeGatewayHint,
    # Kill host `docker mcp gateway` / `docker run ... mcp/` children that thrash RAM.
    # Does not stop BioETL compose containers.
    [switch]$KillHostGateways
)

$ErrorActionPreference = 'Continue'

function Test-EngineUp {
    $ver = docker info --format '{{.ServerVersion}}' 2>$null
    return ($LASTEXITCODE -eq 0 -and $ver)
}

function Test-IsBioetlName {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $true }
    return ($Name -eq 'bioetl' -or $Name -eq 'bioetl-neo4j' -or $Name.StartsWith('bioetl-'))
}

function Test-IsSharedMcpProtected {
    param(
        [string]$Name,
        [string]$SharedLabel,
        [string]$ComposeProject
    )
    if (Test-IsBioetlName $Name) { return $true }
    if ($SharedLabel -eq 'true') { return $true }
    if ($ComposeProject -eq 'bioetl-mcp-shared') { return $true }
    return $false
}

if (-not (Test-EngineUp)) {
    Write-Warning 'Docker engine is not reachable; nothing to clean.'
    exit 1
}

$removed = 0
$ids = docker ps -aq 2>$null
if (-not $ids) {
    Write-Host 'No containers.'
    exit 0
}

foreach ($id in $ids) {
    $meta = docker inspect --format '{{.Name}}|{{.Config.Image}}|{{index .Config.Labels "docker-mcp"}}|{{index .Config.Labels "docker-mcp-name"}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "bioetl.mcp.shared"}}' $id 2>$null
    if (-not $meta) { continue }
    $parts = $meta -split '\|', 6
    $name = ([string]$parts[0]).TrimStart('/')
    $image = [string]$parts[1]
    $dockerMcp = [string]$parts[2]
    $mcpName = [string]$parts[3]
    $composeProject = [string]$parts[4]
    $sharedLabel = [string]$parts[5]

    # Hard allowlist: never touch BioETL compose stacks or shared MCP plane.
    if (Test-IsSharedMcpProtected -Name $name -SharedLabel $sharedLabel -ComposeProject $composeProject) { continue }
    if ($composeProject -match '^bioetl-') { continue }
    if ($image -match 'bioetl-main-bioetl|neo4j:5\.15') { continue }

    $isMcp = $false
    if ($dockerMcp -eq 'true' -or -not [string]::IsNullOrWhiteSpace($mcpName)) { $isMcp = $true }
    if ($image -match '(^|/)mcp/|mcp-server|prometheus-mcp|mcp-grafana|docker-mcp') { $isMcp = $true }
    # Random-name one-shots from docker run --rm that lost the client still match image.
    if (-not $isMcp) { continue }

    $label = if ($mcpName) { $mcpName } else { $image }
    if ($PSCmdlet.ShouldProcess($name, "stop+rm MCP orphan ($label)")) {
        Write-Host "Removing MCP orphan: $name ($label / $image)"
        docker stop $id 2>$null | Out-Null
        docker rm -f $id 2>$null | Out-Null
        $removed++
    }
}

Write-Host "Removed $removed MCP orphan container(s)."

$gatewayProcs = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $c = [string]$_.CommandLine
            $c -match 'mcp gateway' -or
            $c -match 'docker\.exe["\s]+run\b.*mcp/' -or
            $c -match 'docker\.exe".*mcp/brave-search|mcp/grafana|prometheus-mcp'
        }
)

if ($KillHostGateways -and $gatewayProcs.Count -gt 0) {
    Write-Host "Killing $($gatewayProcs.Count) host MCP gateway/run process(es)..."
    foreach ($proc in $gatewayProcs) {
        $cmd = [string]$proc.CommandLine
        if ($cmd.Length -gt 120) { $cmd = $cmd.Substring(0, 120) + '...' }
        if ($PSCmdlet.ShouldProcess("pid=$($proc.ProcessId)", "Stop-Process MCP host child")) {
            Write-Host "  stop pid=$($proc.ProcessId) $cmd"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            # Also kill process tree via taskkill for docker-mcp plugin children.
            & taskkill.exe /PID $proc.ProcessId /F /T 2>$null | Out-Null
        }
    }
} elseif ($IncludeGatewayHint -or $gatewayProcs.Count -gt 0) {
    Write-Host ''
    Write-Host "Host-side MCP gateway/run processes ($($gatewayProcs.Count)):"
    foreach ($proc in $gatewayProcs) {
        $cmd = [string]$proc.CommandLine
        if ($cmd.Length -gt 140) { $cmd = $cmd.Substring(0, 140) + '...' }
        Write-Host ("  pid={0} {1}" -f $proc.ProcessId, $cmd)
    }
    if (-not $KillHostGateways) {
        Write-Host 'Re-run with -KillHostGateways to stop them (AI MCP sessions will drop).'
    }
}

exit 0
