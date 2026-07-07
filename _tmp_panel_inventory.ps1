$ErrorActionPreference = 'Stop'
$ROOT = 'E:\g-drive\05_AI\github\BioactivityDataAcquisition2'
$DASH = Join-Path $ROOT 'grafana\dashboards'
$OUT = Join-Path $ROOT 'docs\03-guides\dashboards\panel-title-inventory.md'

function Get-Panels([object[]]$panels) {
    $disc = New-Object System.Collections.Generic.List[object]
    $stack = New-Object System.Collections.Generic.List[object]
    foreach ($p in $panels) {
        if ($null -ne $p) { [void]$stack.Add($p) }
    }
    while ($stack.Count -gt 0) {
        $panel = $stack[0]
        $stack.RemoveAt(0)
        if ($null -eq $panel) { continue }
        [void]$disc.Add($panel)
        $nested = $panel.panels
        if ($nested) {
            foreach ($item in $nested) {
                if ($null -ne $item) { [void]$stack.Add($item) }
            }
        }
    }
    return $disc
}

$HEADER = @'
# Panel Title Inventory

Generated from `grafana/dashboards/*.json`.

## KPI ownership contract anchors

Machine-readable SSOT: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (`kpi_ownership`).

| KPI key | Canonical UID | Mirror panel(s) |
|---|---|---|
| `failed_runs_in_range` | `bioetl-overview-v2` | `bioetl-runtime#205` |
| `worst_lag_stage` | `bioetl-overview-v2` | `bioetl-runtime#237` |
| `worst_backlog_stage` | `bioetl-overview-v2` | `bioetl-runtime#238` |

| Dashboard | Panel ID | Title |
| --- | ---: | --- |
'@

$rows = New-Object System.Collections.Generic.List[string]
$counts = @{}
Get-ChildItem (Join-Path $DASH '*.json') | Sort-Object Name | ForEach-Object {
    $payload = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $c = 0
    foreach ($panel in (Get-Panels @($payload.panels))) {
        $id = $panel.id
        $title = $panel.title
        if ($null -ne $id -and $title) {
            [void]$rows.Add("| $($_.Name) | $id | $title |")
            $c++
        }
    }
    $counts[$_.Name] = $c
}

$content = $HEADER + ($rows -join "`n") + "`n"
[System.IO.File]::WriteAllText($OUT, $content, [System.Text.UTF8Encoding]::new($false))
Write-Output "wrote $($rows.Count) panel rows -> $OUT"
$counts.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Output "$($_.Name): $($_.Value)" }
Write-Output "TOTAL: $(($counts.Values | Measure-Object -Sum).Sum)"
