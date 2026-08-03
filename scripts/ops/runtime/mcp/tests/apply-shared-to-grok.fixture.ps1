#Requires -Version 5.1
<#
.SYNOPSIS
  Fixture test for apply-shared-to-grok.ps1 (W1.1 / dual-config hardening).

.DESCRIPTION
  Builds a temp Grok-like config.toml where gateway disable previously could
  bleed into neighboring shared servers (Singleline regex). Asserts after
  apply: catalog shared servers enabled=true + localhost URL (including
  docker/mermaid once they are on the shared plane); non-catalog thrash
  gateways disabled when -DisableDockerGateways; neighbor sections intact.
#>
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$mcpDir = Resolve-Path (Join-Path $here '..')
$apply = Join-Path $mcpDir 'apply-shared-to-grok.ps1'
$catalog = Get-Content (Join-Path $mcpDir 'shared-servers.json') -Raw | ConvertFrom-Json
$sharedNames = @($catalog.servers.PSObject.Properties.Name)

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("grok-mcp-fixture-" + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$cfg = Join-Path $tmp 'config.toml'

# Deliberate trap: mixed stdio + disabled shared entries + disabled_mcp_servers
# that incorrectly lists shared names; neighbor section must not be corrupted.
$lines = @(
    '# fixture',
    'disabled_mcp_servers = [',
    '    "docker",',
    '    "fetch",',
    '    "mcp-code-interpreter",',
    ']',
    '',
    '[mcp_servers.docker]',
    'enabled = true',
    "command = 'pwsh'",
    'args = ["-File", "mcp_docker_wrapper.ps1"]',
    'startup_timeout_sec = 180',
    '',
    '[mcp_servers.mermaid]',
    'enabled = true',
    "command = 'pwsh'",
    '',
    '[mcp_servers.context7]',
    'enabled = false',
    "command = 'npx'",
    'args = ["-y", "@upstash/context7-mcp"]',
    '',
    '[mcp_servers.adr-analysis]',
    'enabled = false',
    "command = 'pwsh'",
    '',
    '[mcp_servers.deja]',
    'enabled = false',
    '',
    '[mcp_servers.ast-grep]',
    'enabled = false',
    '',
    '[mcp_servers.brave-search]',
    'enabled = false',
    '',
    # Non-catalog thrash gateway (should be disabled by -DisableDockerGateways
    # only if not in shared catalog — use a synthetic name outside catalog).
    '[mcp_servers.legacy-toolkit-gateway]',
    'enabled = true',
    "command = 'docker'",
    '',
    '[mcp_servers.other]',
    'enabled = true',
    "command = 'echo'"
)
$lines -join "`r`n" | Set-Content -Path $cfg -Encoding utf8

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $apply -GrokConfig $cfg -DisableDockerGateways
if ($LASTEXITCODE -ne 0) {
    Write-Error "apply-shared-to-grok exited $LASTEXITCODE"
    exit 1
}

$text = Get-Content $cfg -Raw -Encoding utf8
$errors = @()

function Get-Section([string]$Name, [string]$Text) {
    $p = "(?m)^\[mcp_servers\.$([regex]::Escape($Name))\]\r?\n(?:(?!^\[).*\r?\n?)*"
    if ($Text -match $p) { return $Matches[0] }
    return $null
}

foreach ($prop in $catalog.servers.PSObject.Properties) {
    $name = $prop.Name
    $port = [int]$prop.Value.port
    $path = [string]$prop.Value.path
    if ([string]::IsNullOrWhiteSpace($path)) { $path = '/mcp' }
    $sec = Get-Section $name $text
    if (-not $sec) { $errors += "missing section $name"; continue }
    if ($sec -notmatch '(?m)^enabled\s*=\s*true\s*$') { $errors += "$name not enabled=true" }
    if ($sec -notmatch [regex]::Escape("http://127.0.0.1:$port$path")) { $errors += "$name bad url" }
    if ($sec -match '(?m)^command\s*=') { $errors += "$name still has command (stdio)" }
}

# Shared catalog gateways stay ENABLED on HTTP (not disabled by -DisableDockerGateways).
foreach ($gw in @('docker', 'mermaid')) {
    if ($sharedNames -notcontains $gw) { continue }
    $sec = Get-Section $gw $text
    if (-not $sec) { $errors += "missing gateway $gw"; continue }
    if ($sec -notmatch '(?m)^enabled\s*=\s*true\s*$') { $errors += "$gw should stay enabled on shared plane" }
    if ($sec -match '(?m)^command\s*=') { $errors += "$gw still stdio" }
}

# Shared names must not remain in disabled_mcp_servers.
if ($text -match '(?ms)^disabled_mcp_servers\s*=\s*\[(.*?)\]') {
    $body = $Matches[1]
    foreach ($n in @('docker', 'fetch')) {
        if ($body -match '"' + [regex]::Escape($n) + '"') {
            $errors += "disabled_mcp_servers still lists shared name $n"
        }
    }
    if ($body -notmatch 'mcp-code-interpreter') {
        $errors += 'disabled_mcp_servers dropped non-shared mcp-code-interpreter'
    }
}

# neighbor must remain enabled=true
$other = Get-Section 'other' $text
if (-not $other -or $other -notmatch '(?m)^enabled\s*=\s*true\s*$') {
    $errors += 'neighbor [mcp_servers.other] was corrupted'
}

if ($errors.Count -gt 0) {
    Write-Host "FAIL:"
    $errors | ForEach-Object { Write-Host "  - $_" }
    Write-Host "--- config ---"
    Write-Host $text
    exit 1
}

Write-Host "PASS: apply-shared-to-grok fixture ($tmp)"
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
exit 0
