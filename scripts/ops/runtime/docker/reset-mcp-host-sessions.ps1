#Requires -Version 5.1
<#
.SYNOPSIS
  Safe-by-default host MCP thrash reset (orphans + optional gateways / extra grok).

.DESCRIPTION
  Default is -WhatIf / dry-run style reporting unless -Execute is passed.
  Never stops bioetl / bioetl-neo4j / bioetl-mcp-* compose or shared containers.

.EXAMPLE
  .\scripts\ops\runtime\docker\reset-mcp-host-sessions.ps1
  .\scripts\ops\runtime\docker\reset-mcp-host-sessions.ps1 -Execute -KillHostGateways
  .\scripts\ops\runtime\docker\reset-mcp-host-sessions.ps1 -Execute -KillExtraGrok
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    # Actually perform destructive actions (without this: report only).
    [switch]$Execute,
    [switch]$KillHostGateways,
    [switch]$KillExtraGrok,
    # Keep this many newest grok.exe processes when -KillExtraGrok (default 1).
    [int]$KeepGrok = 1
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root

Write-Host '=== reset-mcp-host-sessions ==='
Write-Host 'WARNING: Live AI clients respawn MCP after kill. Prefer one client + Toolkit off.'
Write-Host "Mode: $(if ($Execute) { 'EXECUTE' } else { 'REPORT (pass -Execute to apply)' })"

$grok = @(Get-Process -Name 'grok' -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending)
Write-Host "grok.exe count: $($grok.Count) (keep newest $KeepGrok if -KillExtraGrok)"
foreach ($g in $grok) {
    Write-Host ("  pid={0} start={1} wsMB={2}" -f $g.Id, $g.StartTime, [math]::Round($g.WS/1MB,0))
}

if ($Execute -and $KillExtraGrok -and $grok.Count -gt $KeepGrok) {
    $victims = $grok | Select-Object -Skip $KeepGrok
    foreach ($v in $victims) {
        if ($PSCmdlet.ShouldProcess("grok pid=$($v.Id)", 'Stop-Process')) {
            Write-Host "Stopping extra grok pid=$($v.Id)"
            Stop-Process -Id $v.Id -Force -ErrorAction SilentlyContinue
        }
    }
} elseif ($KillExtraGrok -and -not $Execute) {
    Write-Host 'Would stop extra grok processes with -Execute -KillExtraGrok'
}

$cleanup = Join-Path $PSScriptRoot 'cleanup-mcp-orphans.ps1'
if (Test-Path $cleanup) {
    $cargs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $cleanup, '-IncludeGatewayHint')
    if ($Execute -and $KillHostGateways) {
        $cargs += '-KillHostGateways'
    }
    if (-not $Execute) {
        $cargs += '-WhatIf'
    }
    Write-Host 'Running cleanup-mcp-orphans...'
    & powershell.exe @cargs
} else {
    Write-Warning "cleanup script missing: $cleanup"
}

Write-Host @'

Operator checklist (today, no shared HTTP required):
  1) Leave one grok.exe (use -Execute -KillExtraGrok or close UI)
  2) Docker Desktop → MCP Toolkit: disable jetbrains / node-code-sandbox / default
  3) Restart the remaining AI client after apply-docker-stable-mcp -Profile stable
  4) When idle: cleanup-mcp-orphans.ps1 -KillHostGateways
  5) Avoid parallel Grok + Cursor + WSL-Codex with heavy MCP

Shared HTTP multi-client path (program #6563):
  .\scripts\ops\runtime\mcp\start-shared.ps1
  python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation

See docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md
'@
exit 0
