#Requires -Version 5.1
<#
.SYNOPSIS
  Apply Docker-stable MCP posture on this host (profile + orphan cleanup).

.DESCRIPTION
  1) Regenerates *local* IDE MCP projections with --profile stable|core
     (tracked .mcp.json stays full SSOT).
  2) Stops/removes orphan mcp/* / docker-mcp labeled containers.
  3) Optionally runs ensure-stable for bioetl (+ neo4j).

.EXAMPLE
  .\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1
  .\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1 -Profile core -WithNeo4j
#>
[CmdletBinding()]
param(
    [ValidateSet('stable', 'core', 'ops', 'graph', 'full')]
    [string]$Profile = 'stable',
    [switch]$WithNeo4j,
    [switch]$SkipEnsureStable,
    [switch]$SkipSetupMcp,
    [switch]$KillHostGateways
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

Write-Host "=== apply-docker-stable-mcp profile=$Profile ==="

if (-not $SkipSetupMcp) {
    $setup = Join-Path $Root 'scripts\ai\codex\setup_mcp.py'
    if (Test-Path $setup) {
        Write-Host "Materializing local MCP projections with --profile $Profile ..."
        # Tracked portable inventory remains full; only local IDE projections filter.
        $prevPy = $env:PYTHONPATH
        if ($prevPy) {
            $env:PYTHONPATH = "$Root;$prevPy"
        } else {
            $env:PYTHONPATH = $Root
        }
        try {
            & python $setup --profile $Profile --skip-codex-validation 2>&1 | ForEach-Object { Write-Host $_ }
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "setup_mcp.py exited $LASTEXITCODE (local projections may be partial)"
            }
        } finally {
            if ($null -eq $prevPy) {
                Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
            } else {
                $env:PYTHONPATH = $prevPy
            }
        }
    } else {
        Write-Warning "setup_mcp.py not found: $setup"
    }
}

$cleanup = Join-Path $PSScriptRoot 'cleanup-mcp-orphans.ps1'
if (Test-Path $cleanup) {
    Write-Host 'Cleaning MCP orphan containers...'
    $cargs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $cleanup, '-IncludeGatewayHint')
    if ($KillHostGateways) { $cargs += '-KillHostGateways' }
    & powershell.exe @cargs
}

if (-not $SkipEnsureStable) {
    $ensure = Join-Path $PSScriptRoot 'ensure-stable.ps1'
    $ensureArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ensure, '-SkipHostHarden')
    if ($WithNeo4j) { $ensureArgs += '-WithNeo4j' }
    Write-Host 'Ensuring BioETL stacks (no WSL hard restart)...'
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $ensureArgs `
        -WorkingDirectory $Root -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) {
        Write-Warning "ensure-stable exit=$($p.ExitCode)"
        exit $p.ExitCode
    }
}

Write-Host @'

Done. Docker-stable MCP posture:
  - Local IDE MCP profile: use setup_mcp --profile stable|core (this run applied it)
  - Orphan mcp/* containers removed
  - BioETL stacks: ensure-stable (unless -SkipEnsureStable)

Restart AI clients (Grok/Cursor/Codex) so they reload the slimmer MCP list.
Tracked .mcp.json remains the full portable inventory by design.
'@
exit 0
