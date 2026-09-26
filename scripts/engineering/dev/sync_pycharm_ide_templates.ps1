# Sync portable PyCharm templates from configs/ide/pycharm into local .idea/
# Does NOT overwrite machine-local surfaces (workspace.xml, .iml, shelves, etc.)
# unless -ForceAll is passed.
#
# Usage:
#   .\scripts\engineering\dev\sync_pycharm_ide_templates.ps1
#   .\scripts\engineering\dev\sync_pycharm_ide_templates.ps1 -DryRun
#   .\scripts\engineering\dev\sync_pycharm_ide_templates.ps1 -SkipPolicyCheck

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$ForceAll,
    [switch]$SkipPolicyCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$InformationPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
Set-Location $RepoRoot

$SourceRoot = Join-Path $RepoRoot "configs\ide\pycharm"
$DestRoot = Join-Path $RepoRoot ".idea"

$RequiredRunConfigs = @(
    "Pytest_Fast.xml",
    "Pytest_Full.xml",
    "Pytest_Coverage.xml",
    "Pytest_Debug.xml",
    "Pytest_Architecture.xml",
    "Pytest_Architecture_Slow_Governance.xml",
    "Mypy_Full.xml",
    "Ruff_Check.xml",
    "Ruff_Format_Check.xml",
    "Quality_Gate.xml",
    "BioETL_Smoke_Offline.xml"
)

$SharedRelativePaths = @(
    "codeStyles",
    "inspectionProfiles",
    "runConfigurations",
    "pyLspTools.xml"
)

function Write-Log {
    param([string]$Level, [string]$Message)
    Write-Information "[sync_pycharm_ide_templates][$Level] $Message" -InformationAction Continue
}

function Get-SharedRunConfigFileFailures {
    param(
        [string]$Name,
        [string]$Text
    )

    $failures = New-Object System.Collections.Generic.List[string]
    if ($Text -match 'name="PYTHONPATH"') {
        [void]$failures.Add("${Name}: forbidden PYTHONPATH env")
    }
    if ($Text -match 'ADD_CONTENT_ROOTS" value="true"') {
        [void]$failures.Add("${Name}: ADD_CONTENT_ROOTS must be false")
    }
    if ($Text -match 'ADD_SOURCE_ROOTS" value="true"') {
        [void]$failures.Add("${Name}: ADD_SOURCE_ROOTS must be false")
    }

    $isPytest = ($Text -match 'factoryName="py\.test"') -or ($Text -match 'type="tests"')
    $isCoverageConfig = ($Name -eq "Pytest_Coverage.xml") -or ($Text -match 'name="pytest-coverage"')
    if ($isPytest -and -not $isCoverageConfig) {
        if ($Text -notmatch '--no-cov') {
            [void]$failures.Add("${Name}: non-coverage pytest config must include --no-cov")
        }
        if ($Text -match '--cov(=|\s)') {
            [void]$failures.Add("${Name}: --cov is only allowed on pytest-coverage")
        }
    }
    if ($isCoverageConfig -and $Text -notmatch '--cov=') {
        [void]$failures.Add("${Name}: pytest-coverage must include --cov=")
    }
    return ,$failures
}

function Test-SharedRunConfigPolicy {
    param([string]$RunConfigDir)

    $failures = New-Object System.Collections.Generic.List[string]
    $xmlFiles = Get-ChildItem -Path $RunConfigDir -Filter "*.xml" -File -ErrorAction Stop

    foreach ($file in $xmlFiles) {
        $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop
        foreach ($f in (Get-SharedRunConfigFileFailures -Name $file.Name -Text $text)) {
            [void]$failures.Add($f)
        }
    }

    foreach ($required in $RequiredRunConfigs) {
        $path = Join-Path $RunConfigDir $required
        if (-not (Test-Path -LiteralPath $path)) {
            [void]$failures.Add("missing required shared run config: $required")
        }
    }

    return ,$failures
}

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    Write-Log "error" "Source templates not found: $SourceRoot"
    exit 1
}

$runConfigDir = Join-Path $SourceRoot "runConfigurations"
if (-not $SkipPolicyCheck) {
    if (-not (Test-Path -LiteralPath $runConfigDir)) {
        Write-Log "error" "Missing shared runConfigurations at $runConfigDir"
        exit 1
    }
    $policyFailures = Test-SharedRunConfigPolicy -RunConfigDir $runConfigDir
    if ($policyFailures.Count -gt 0) {
        Write-Log "error" "Shared template policy check failed:"
        foreach ($f in $policyFailures) {
            Write-Host "  - $f"
        }
        exit 2
    }
    Write-Log "ok" "Shared runConfiguration policy check passed"
}

if (-not (Test-Path -LiteralPath $DestRoot)) {
    if ($DryRun) {
        Write-Log "dry-run" "Would create $DestRoot"
    } else {
        New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null
        Write-Log "ok" "Created $DestRoot"
    }
}

$planned = New-Object System.Collections.Generic.List[string]

if ($ForceAll) {
    Write-Log "warn" "-ForceAll copies entire shared tree; still avoid committing machine-local .idea state"
    Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
        [void]$planned.Add($_.Name)
    }
} else {
    foreach ($rel in $SharedRelativePaths) {
        $src = Join-Path $SourceRoot $rel
        if (-not (Test-Path -LiteralPath $src)) {
            Write-Log "error" "Expected shared surface missing: $rel"
            exit 1
        }
        [void]$planned.Add($rel)
    }
}

foreach ($rel in $planned) {
    $src = Join-Path $SourceRoot $rel
    $dst = Join-Path $DestRoot $rel
    if ($DryRun) {
        Write-Log "dry-run" "Would sync $rel -> .idea\$rel"
        continue
    }

    if (Test-Path -LiteralPath $src -PathType Container) {
        if (-not (Test-Path -LiteralPath $dst)) {
            New-Item -ItemType Directory -Force -Path $dst | Out-Null
        }
        Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
    } else {
        $parent = Split-Path -Parent $dst
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
    Write-Log "ok" "Synced $rel"
}

if (-not $DryRun) {
    $destRun = Join-Path $DestRoot "runConfigurations"
    foreach ($required in $RequiredRunConfigs) {
        $path = Join-Path $destRun $required
        if (-not (Test-Path -LiteralPath $path)) {
            Write-Log "error" "After sync missing: .idea\runConfigurations\$required"
            exit 3
        }
    }
}

Write-Host ""
Write-Log "hint" "Post-sync checklist:"
Write-Host "  1. Interpreter: `$PROJECT_DIR`\.venv-win\Scripts\python.exe (editable install, no PYTHONPATH)"
Write-Host "  2. Run Configurations: pytest-fast, pytest-architecture, pytest-architecture-slow-governance, pytest-debug, pytest-coverage, mypy-full, ruff-check, quality-gate, BioETL smoke (offline fixture)"
Write-Host "  3. Formatter: Ruff only (Black disabled in Actions on Save)"
Write-Host "  4. AI: exactly one inline completion provider"
Write-Host "  5. Do not commit .idea/workspace.xml, shelves, SDK paths, MCP tokens, or .env"
Write-Host "  6. Docs: docs/03-guides/development/pycharm-setup.md"
if ($DryRun) {
    Write-Log "ok" "Dry-run complete (no files written)"
} else {
    Write-Log "ok" "Sync complete"
}
