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
  .\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -KillHostGateways
  .\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -ForceAllForeign -KillHostGateways
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$IncludeGatewayHint,
    # Kill host `docker mcp gateway` / `docker run ... mcp/` children that thrash RAM.
    # Does not stop BioETL compose containers.
    [switch]$KillHostGateways,
    # Also kill host `docker run ... mcp/*` children (stdio thrash).
    # Off by default: shared brave plane uses the same docker-run path.
    [switch]$KillDockerRunMcp,
    # Remove ANY non-bioetl container (Toolkit thrash with missing labels / digests).
    [switch]$ForceAllForeign
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
    if ($ComposeProject -match '^bioetl-') { return $true }
    return $false
}

if (-not (Test-EngineUp)) {
    Write-Warning 'Docker engine is not reachable; nothing to clean.'
    exit 1
}

$removed = 0
# Prefer name-based pass (reliable under thrash); IDs can flake when engine is OOM-ish.
$names = @(docker ps -a --format '{{.Names}}' 2>$null | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
if ($names.Count -eq 0) {
    Write-Host 'No containers.'
} else {
    foreach ($name in $names) {
        if (Test-IsBioetlName $name) {
            continue
        }
        $meta = docker inspect --format '{{.Id}}|{{.Config.Image}}|{{index .Config.Labels "docker-mcp"}}|{{index .Config.Labels "docker-mcp-name"}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "bioetl.mcp.shared"}}|{{index .Config.Labels "bioetl.mcp"}}|{{index .Config.Labels "docker-mcp-transport"}}' $name 2>$null
        if (-not $meta) {
            # Name known to docker ps but inspect failed: still force-rm if requested.
            if ($ForceAllForeign -and $PSCmdlet.ShouldProcess($name, 'rm -f (inspect failed)')) {
                Write-Host "Removing foreign (inspect failed): $name"
                docker rm -f $name 2>$null | Out-Null
                $removed++
            }
            continue
        }
        $parts = $meta -split '\|', 8
        $id = [string]$parts[0]
        $image = [string]$parts[1]
        $dockerMcp = [string]$parts[2]
        $mcpName = [string]$parts[3]
        $composeProject = [string]$parts[4]
        $sharedLabel = [string]$parts[5]
        $bioetlMcp = [string]$parts[6]
        $mcpTransport = [string]$parts[7]

        if (Test-IsSharedMcpProtected -Name $name -SharedLabel $sharedLabel -ComposeProject $composeProject) {
            continue
        }
        if ($image -match 'bioetl-main-bioetl|neo4j:5\.15') { continue }

        $isMcp = $false
        if ($dockerMcp -eq 'true') { $isMcp = $true }
        if ($mcpName -and $mcpName -ne '<no value>') { $isMcp = $true }
        if ($bioetlMcp -and $bioetlMcp -ne '<no value>') { $isMcp = $true }
        if ($mcpTransport -and $mcpTransport -ne '<no value>') { $isMcp = $true }
        if ($image -match '(^|/)mcp/|mcp-server|prometheus-mcp|mcp-grafana|docker-mcp') { $isMcp = $true }
        if ($mcpName -match 'jetbrains|node-code-sandbox|brave|grafana|prometheus') { $isMcp = $true }
        if ($ForceAllForeign) { $isMcp = $true }
        if (-not $isMcp) { continue }

        $label = if ($mcpName -and $mcpName -ne '<no value>') { $mcpName } elseif ($bioetlMcp -and $bioetlMcp -ne '<no value>') { $bioetlMcp } else { $image }
        if ($PSCmdlet.ShouldProcess($name, "stop+rm MCP orphan ($label)")) {
            Write-Host "Removing MCP orphan: $name ($label / $image)"
            docker rm -f $name 2>$null | Out-Null
            if ($id) { docker rm -f $id 2>$null | Out-Null }
            $removed++
        }
    }
}

Write-Host "Removed $removed MCP orphan container(s)."

$hostProcs = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $c = [string]$_.CommandLine
            if ([string]::IsNullOrWhiteSpace($c)) { return $false }
            $isGateway = ($c -match 'mcp gateway') -or ($c -match 'docker-mcp\.exe.*gateway')
            $isDockerRunMcp = (
                $c -match 'docker\.exe["\s]+run\b.*mcp/' -or
                $c -match 'docker\.exe".*mcp/brave-search|mcp/grafana|prometheus-mcp' -or
                $c -match 'docker\.exe.*--label\s+bioetl\.mcp='
            )
            if ($isGateway) { return $true }
            if ($isDockerRunMcp -and $KillDockerRunMcp) { return $true }
            return $false
        }
)

# When only listing, show both gateway and docker-run thrash.
$listProcs = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $c = [string]$_.CommandLine
            $c -match 'mcp gateway' -or
            $c -match 'docker-mcp\.exe' -or
            $c -match 'docker\.exe["\s]+run\b.*mcp/' -or
            $c -match 'docker\.exe.*mcp/brave-search' -or
            $c -match 'docker\.exe.*--label\s+bioetl\.mcp='
        }
)

if ($KillHostGateways -and $hostProcs.Count -gt 0) {
    Write-Host "Killing $($hostProcs.Count) host MCP process(es) (gateways$(if ($KillDockerRunMcp) { '+docker-run' } else { '' }))..."
    foreach ($proc in $hostProcs) {
        $cmd = [string]$proc.CommandLine
        if ($cmd.Length -gt 120) { $cmd = $cmd.Substring(0, 120) + '...' }
        if ($PSCmdlet.ShouldProcess("pid=$($proc.ProcessId)", "Stop-Process MCP host child")) {
            Write-Host "  stop pid=$($proc.ProcessId) $cmd"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            & taskkill.exe /PID $proc.ProcessId /F /T 2>$null | Out-Null
        }
    }
} elseif ($IncludeGatewayHint -or $listProcs.Count -gt 0) {
    Write-Host ''
    Write-Host "Host-side MCP processes ($($listProcs.Count)):"
    foreach ($proc in $listProcs) {
        $cmd = [string]$proc.CommandLine
        if ($cmd.Length -gt 140) { $cmd = $cmd.Substring(0, 140) + '...' }
        Write-Host ("  pid={0} {1}" -f $proc.ProcessId, $cmd)
    }
    if (-not $KillHostGateways) {
        Write-Host 'Re-run with -KillHostGateways to stop gateway processes (AI MCP sessions will drop).'
        Write-Host 'Add -KillDockerRunMcp only when shared brave plane is stopped (kills stdio docker-run thrash).'
    }
}

exit 0
