#Requires -Version 5.1
<#
.SYNOPSIS
  Point Grok at BioETL shared Streamable HTTP MCP plane (one process per server).

.DESCRIPTION
  Rewrites [mcp_servers.<name>] for catalog shared-servers.json entries from
  stdio (command/args) to url = "http://127.0.0.1:<port>/mcp" so multiple Grok
  processes share one long-running server each.

  By default updates BOTH:
    - ~/.grok/config.toml (user)
    - <repo>/.grok/config.toml (project; gitignored) when present

  Project config often still has stdio wrappers and OVERRIDES/duplicates user
  HTTP URLs — that was the main multi-spawn source on this host.

  Always forces enabled = true for catalog shared servers and removes those
  names from disabled_mcp_servers if present.
  -DisableDockerGateways disables thrash stdio gateways that are NOT on the
  shared catalog (never disables catalog entries).

  Backs up each config.toml before edit. Does not start the plane (use start-shared.ps1).

.EXAMPLE
  .\scripts\ops\runtime\mcp\start-shared.ps1
  .\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1
  # reload MCP in Grok (/mcps then r) or restart all Grok windows
#>
# SupportsShouldProcess provides -WhatIf / -Confirm automatically — do not redeclare.
[CmdletBinding(SupportsShouldProcess)]
param(
    # Single file override. Empty = user + project (if exists).
    [string]$GrokConfig = '',
    # Disable non-catalog stdio gateway thrash only.
    [switch]$DisableDockerGateways,
    # Only touch ~/.grok/config.toml (skip repo .grok/config.toml).
    [switch]$UserOnly
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$catalogPath = Join-Path $PSScriptRoot 'shared-servers.json'
if (-not (Test-Path $catalogPath)) {
    Write-Error "Missing $catalogPath"
    exit 1
}
$catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json

$sharedNames = @($catalog.servers.PSObject.Properties.Name)

function Get-SharedBlock {
    param([string]$Name, [int]$Port, [string]$Path = '/mcp', [int]$Timeout = 180)
    $url = "http://127.0.0.1:$Port$Path"
    return @"
[mcp_servers.$Name]
enabled = true
url = "$url"
startup_timeout_sec = $Timeout

"@
}

function Get-McpServerSectionPattern {
    param([string]$Name)
    # Section body: lines that do NOT start a new TOML table. No Singleline
    # bleed into the next [mcp_servers.*] (W1.1 root-cause fix).
    return "(?m)^\[mcp_servers\.$([regex]::Escape($Name))\]\r?\n(?:(?!^\[).*\r?\n?)*"
}

function Set-SectionEnabled {
    param(
        [string]$Text,
        [string]$Name,
        [bool]$Enabled
    )
    $val = if ($Enabled) { 'true' } else { 'false' }
    $pattern = Get-McpServerSectionPattern -Name $Name
    if ($Text -notmatch $pattern) {
        return @{ Text = $Text; Changed = $false }
    }
    $section = $Matches[0]
    if ($section -match '(?m)^enabled\s*=') {
        $newSection = [regex]::Replace($section, '(?m)^enabled\s*=\s*.*$', "enabled = $val", 1)
    } else {
        $newSection = [regex]::Replace(
            $section,
            "(?m)^(\[mcp_servers\.$([regex]::Escape($Name))\])\r?\n",
            "`$1`r`nenabled = $val`r`n",
            1
        )
    }
    if ($newSection -eq $section) {
        return @{ Text = $Text; Changed = $false }
    }
    $newText = [regex]::Replace($Text, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{
        param($m)
        return $newSection
    }, 1)
    return @{ Text = $newText; Changed = $true }
}

function Remove-SharedFromDisabledList {
    param(
        [string]$Text,
        [string[]]$Names
    )
    if ($Text -notmatch '(?ms)^disabled_mcp_servers\s*=\s*\[(.*?)\]') {
        return @{ Text = $Text; Changed = $false; Removed = @() }
    }
    $full = $Matches[0]
    $body = $Matches[1]
    $removed = @()
    $newBody = $body
    foreach ($n in $Names) {
        $pat = '(?m)^\s*"' + [regex]::Escape($n) + '"\s*,?\s*\r?\n?'
        if ($newBody -match $pat) {
            $newBody = [regex]::Replace($newBody, $pat, '', 1)
            $removed += $n
        }
    }
    # Drop trailing comma before ]
    $newBody = [regex]::Replace($newBody, ',(\s*)$', '$1')
    if ($removed.Count -eq 0) {
        return @{ Text = $Text; Changed = $false; Removed = @() }
    }
    $newFull = "disabled_mcp_servers = [$newBody]"
    # Keep array multi-line shape if original was multi-line
    if ($full -match "`n") {
        $items = @([regex]::Matches($newBody, '(?m)^\s*"[^"]+"') | ForEach-Object { $_.Value.Trim() })
        if ($items.Count -eq 0) {
            $newFull = "disabled_mcp_servers = []"
        } else {
            $inner = ($items | ForEach-Object { "    $_," }) -join "`r`n"
            $inner = $inner -replace ',\s*$', ''
            $newFull = "disabled_mcp_servers = [`r`n$inner`r`n]"
        }
    }
    $newText = $Text.Replace($full, $newFull)
    return @{ Text = $newText; Changed = $true; Removed = $removed }
}

function Update-OneGrokConfig {
    param(
        [string]$ConfigPath,
        [switch]$DisableGateways
    )
    if (-not (Test-Path $ConfigPath)) {
        Write-Warning "Skip missing: $ConfigPath"
        return @{ Ok = $false; Changed = @() }
    }

    Write-Host "=== $ConfigPath ==="
    $raw = Get-Content $ConfigPath -Raw -Encoding utf8
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = "$ConfigPath.bak-shared-$stamp"
    if (-not $WhatIfPreference) {
        Copy-Item -Path $ConfigPath -Destination $backup -Force
        Write-Host "Backup: $backup"
    }

    $updated = $raw
    $changed = @()
    foreach ($prop in $catalog.servers.PSObject.Properties) {
        $name = $prop.Name
        $port = [int]$prop.Value.port
        $path = [string]$prop.Value.path
        if ([string]::IsNullOrWhiteSpace($path)) { $path = '/mcp' }
        $block = Get-SharedBlock -Name $name -Port $port -Path $path

        $pattern = Get-McpServerSectionPattern -Name $name
        if ($updated -match $pattern) {
            $updated = [regex]::Replace($updated, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{
                param($m)
                return $block
            }, 1)
            $changed += $name
            Write-Host "  rewrite $name -> http://127.0.0.1:$port$path (enabled=true)"
        } else {
            if ($updated -notmatch "(?m)^\[mcp_servers\.$([regex]::Escape($name))\]") {
                if (-not $updated.EndsWith("`n")) { $updated += "`n" }
                $updated += "`n" + $block
                $changed += $name
                Write-Host "  append $name -> http://127.0.0.1:$port$path (enabled=true)"
            }
        }
    }

    foreach ($name in $sharedNames) {
        $r = Set-SectionEnabled -Text $updated -Name $name -Enabled $true
        $updated = $r.Text
        if ($r.Changed) {
            Write-Host "  assert enabled=true -> $name"
        }
    }

    $d = Remove-SharedFromDisabledList -Text $updated -Names $sharedNames
    $updated = $d.Text
    if ($d.Changed) {
        Write-Host ("  removed from disabled_mcp_servers: {0}" -f ($d.Removed -join ', '))
    }

    if ($DisableGateways) {
        foreach ($gw in @('docker', 'mermaid', 'dockerhub', 'grafana', 'prometheus')) {
            if ($sharedNames -contains $gw) {
                Write-Host "  skip disable $gw (present on shared catalog)"
                continue
            }
            $r = Set-SectionEnabled -Text $updated -Name $gw -Enabled $false
            $updated = $r.Text
            if ($r.Changed) {
                Write-Host "  disable $gw (stdio gateway thrash)"
            }
        }
    }

    $verifyFailed = @()
    foreach ($prop in $catalog.servers.PSObject.Properties) {
        $name = $prop.Name
        $port = [int]$prop.Value.port
        $path = [string]$prop.Value.path
        if ([string]::IsNullOrWhiteSpace($path)) { $path = '/mcp' }
        $expectUrl = "http://127.0.0.1:$port$path"
        $pat = Get-McpServerSectionPattern -Name $name
        if ($updated -notmatch $pat) {
            $verifyFailed += "$name (section missing)"
            continue
        }
        $sec = $Matches[0]
        if ($sec -notmatch '(?m)^enabled\s*=\s*true\s*$') {
            $verifyFailed += "$name (enabled != true)"
        }
        if ($sec -notmatch [regex]::Escape($expectUrl)) {
            $verifyFailed += "$name (url missing $expectUrl)"
        }
    }
    if ($verifyFailed.Count -gt 0) {
        Write-Error ("Shared plane verification failed for ${ConfigPath}: " + ($verifyFailed -join '; '))
        return @{ Ok = $false; Changed = $changed }
    }

    if ($changed.Count -eq 0 -and -not $d.Changed) {
        Write-Warning "No mcp_servers sections matched in $ConfigPath; unchanged."
        return @{ Ok = $true; Changed = @() }
    }

    if ($WhatIfPreference) {
        Write-Host "WhatIf: would update $($changed.Count) servers in $ConfigPath : $($changed -join ', ')"
        return @{ Ok = $true; Changed = $changed }
    }

    $updated = $updated -replace "`r`n", "`n"
    $updated = $updated -replace "`n", "`r`n"
    if ($PSCmdlet.ShouldProcess($ConfigPath, "Write shared HTTP MCP URLs for: $($changed -join ', ')")) {
        [System.IO.File]::WriteAllText($ConfigPath, $updated)
        Write-Host "Updated $ConfigPath ($($changed.Count) servers: $($changed -join ', '))"
    }
    return @{ Ok = $true; Changed = $changed }
}

# Resolve target files
$targets = @()
if (-not [string]::IsNullOrWhiteSpace($GrokConfig)) {
    $targets = @($GrokConfig)
} else {
    $userCfg = Join-Path $env:USERPROFILE '.grok\config.toml'
    $projectCfg = Join-Path $Root '.grok\config.toml'
    if (Test-Path $userCfg) { $targets += $userCfg }
    if (-not $UserOnly -and (Test-Path $projectCfg)) { $targets += $projectCfg }
}

if ($targets.Count -eq 0) {
    Write-Error 'No Grok config.toml found (user or project).'
    exit 1
}

$anyFail = $false
$totalChanged = 0
foreach ($t in $targets) {
    $res = Update-OneGrokConfig -ConfigPath $t -DisableGateways:$DisableDockerGateways
    if (-not $res.Ok) { $anyFail = $true }
    $totalChanged += @($res.Changed).Count
}

if ($anyFail) { exit 2 }
if ($totalChanged -eq 0 -and -not $WhatIfPreference) {
    Write-Warning 'No server rewrites applied (configs may already be shared).'
}
Write-Host 'Verified: catalog shared servers have enabled=true + localhost URL where present.'
Write-Host 'Reload MCP in Grok (/mcps then r) or restart ALL Grok windows so stdio children stop respawning.'
exit 0
