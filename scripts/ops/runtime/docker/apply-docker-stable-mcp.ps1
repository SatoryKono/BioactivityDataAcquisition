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
    [ValidateSet('stable', 'shared', 'core', 'ops', 'graph', 'full')]
    [string]$Profile = 'stable',
    [ValidateSet('stdio', 'shared', 'hybrid')]
    [string]$TransportMode = 'stdio',
    [switch]$WithSharedMcp,
    [switch]$WithNeo4j,
    [switch]$SkipEnsureStable,
    [switch]$SkipSetupMcp,
    [switch]$KillHostGateways,
    # Remove any non-bioetl container (Toolkit thrash / digest-only images).
    [switch]$ForceAllForeign
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

if ($WithSharedMcp -and $TransportMode -eq 'stdio') {
    $TransportMode = 'shared'
    if ($Profile -eq 'stable') { $Profile = 'shared' }
}

Write-Host "=== apply-docker-stable-mcp profile=$Profile transport=$TransportMode ==="

if ($WithSharedMcp) {
    $startShared = Join-Path $Root 'scripts\ops\runtime\mcp\start-shared.ps1'
    if (Test-Path $startShared) {
        Write-Host 'Starting shared MCP plane...'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startShared 2>&1 | ForEach-Object { Write-Host $_ }
    } else {
        Write-Warning "start-shared.ps1 not found: $startShared"
    }
}

if (-not $SkipSetupMcp) {
    $setup = Join-Path $Root 'scripts\ai\codex\setup_mcp.py'
    if (Test-Path $setup) {
        Write-Host "Materializing local MCP projections with --profile $Profile --transport-mode $TransportMode ..."
        # Tracked portable inventory remains full; only local IDE projections filter.
        $prevPy = $env:PYTHONPATH
        if ($prevPy) {
            $env:PYTHONPATH = "$Root;$prevPy"
        } else {
            $env:PYTHONPATH = $Root
        }
        try {
            & python $setup --profile $Profile --transport-mode $TransportMode --skip-codex-validation 2>&1 | ForEach-Object { Write-Host $_ }
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
    if ($ForceAllForeign) { $cargs += '-ForceAllForeign' }
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

Write-Host @"

Done. Docker-stable MCP posture:
  - Local IDE MCP profile=$Profile transport=$TransportMode
  - Shared plane: $(if ($WithSharedMcp) { 'start-shared invoked' } else { 'not requested (-WithSharedMcp)' })
  - Orphan mcp/* containers removed (bioetl-* / bioetl.mcp.shared protected)
  - BioETL stacks: ensure-stable (unless -SkipEnsureStable)

Restart AI clients (Grok/Cursor/Codex) so they reload MCP config.
Tracked .mcp.json remains the full portable inventory by design.
See docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md
"@
exit 0
