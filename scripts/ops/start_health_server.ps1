#!/usr/bin/env pwsh
param(
    [string]$ListenHost = "0.0.0.0",
    [int]$ListenPort = 8081,
    [switch]$SkipEditableInstall,
    [switch]$PreflightOnly,
    [string]$ProbeRunId = "",
    [string]$ProbePipeline = "chembl_activity",
    [string]$ProbeReasonCode = "range_filter_mismatch",
    [string]$ProbeField = "pchembl_value",
    [string]$ProbeFrom = "2026-04-05T11:11:11.107Z",
    [string]$ProbeTo = "2026-04-06T11:11:11.107Z"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
}

function Resolve-RepoPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $candidates = @(
        (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
        (Join-Path $RepoRoot ".venv-win\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "Python venv not found. Expected one of: $($candidates -join ', ')"
}

function Get-FilteredReadsModulePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    return (& $PythonExe -c "import bioetl.infrastructure.quarantine.filtered_reads as f; print(f.__file__)")
}

function Invoke-RunTypeProbe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$Pipeline,
        [Parameter(Mandatory = $true)]
        [string]$ReasonCode,
        [Parameter(Mandatory = $true)]
        [string]$Field,
        [Parameter(Mandatory = $true)]
        [string]$RunId,
        [Parameter(Mandatory = $true)]
        [string]$FromTs,
        [Parameter(Mandatory = $true)]
        [string]$ToTs
    )

    $env:PROBE_PIPELINE = $Pipeline
    $env:PROBE_REASON_CODE = $ReasonCode
    $env:PROBE_FIELD = $Field
    $env:PROBE_RUN_ID = $RunId
    $env:PROBE_FROM = $FromTs
    $env:PROBE_TO = $ToTs

    $probeScript = @'
import asyncio
import json
import os
from bioetl.composition.services_api import get_quarantine_service


async def main() -> None:
    service = get_quarantine_service()
    payload = await service.get_filtered_filter_options(
        pipeline=os.environ["PROBE_PIPELINE"],
        reason_code=os.environ["PROBE_REASON_CODE"],
        field=os.environ["PROBE_FIELD"],
        run_id=os.environ["PROBE_RUN_ID"],
        from_ts=os.environ["PROBE_FROM"],
        to_ts=os.environ["PROBE_TO"],
    )
    print(json.dumps(payload, ensure_ascii=True))


asyncio.run(main())
'@

    $tempPy = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".py")
    try {
        Set-Content -Path $tempPy -Value $probeScript -Encoding UTF8
        $jsonText = & $PythonExe $tempPy
        return ($jsonText | ConvertFrom-Json)
    } finally {
        if (Test-Path $tempPy) {
            Remove-Item -Path $tempPy -Force -ErrorAction SilentlyContinue
        }
    }
}

$repoRoot = Get-RepoRoot
Set-Location $repoRoot

$pythonExe = Resolve-RepoPython -RepoRoot $repoRoot
Write-Host "[INFO] Repo root: $repoRoot"
Write-Host "[INFO] Python: $pythonExe"

if (-not $SkipEditableInstall) {
    Write-Host "[INFO] Running editable install (pip install -e .)"
    & $pythonExe -m pip install -e .
}

$modulePath = Get-FilteredReadsModulePath -PythonExe $pythonExe
Write-Host "[INFO] filtered_reads module: $modulePath"

if ($ProbeRunId) {
    Write-Host "[INFO] Probing filter-options run_types for run_id=$ProbeRunId"
    $probe = Invoke-RunTypeProbe `
        -PythonExe $pythonExe `
        -Pipeline $ProbePipeline `
        -ReasonCode $ProbeReasonCode `
        -Field $ProbeField `
        -RunId $ProbeRunId `
        -FromTs $ProbeFrom `
        -ToTs $ProbeTo

    $runTypes = @($probe.run_types)
    Write-Host "[INFO] Probe run_types: $($runTypes -join ', ')"
}

if ($PreflightOnly) {
    Write-Host "[INFO] Preflight completed. Server not started because -PreflightOnly was set."
    exit 0
}

Write-Host "[INFO] Starting health server on http://${ListenHost}:${ListenPort}"
& $pythonExe -m bioetl health server --host $ListenHost --port $ListenPort
