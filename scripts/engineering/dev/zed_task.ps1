# Zed task launcher for BioETL (Windows PowerShell).
# Does not require `uv` on PATH. Prefers .venv-win project Python.
#
# Usage:
#   .\scripts\engineering\dev\zed_task.ps1 -Module pytest -- tests/smoke -q
#   .\scripts\engineering\dev\zed_task.ps1 -Module ruff -- format .
#   .\scripts\engineering\dev\zed_task.ps1 -Script scripts/ai/codex/setup_mcp.py -- --skip-codex
#   .\scripts\engineering\dev\zed_task.ps1 -Exe lint-imports -- --config pyproject.toml

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Module,

    [Parameter(Mandatory = $false)]
    [string]$Script,

    [Parameter(Mandatory = $false)]
    [string]$Exe,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ToolArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
Set-Location $RepoRoot

function Get-ProjectPython {
    $candidates = @(
        (Join-Path $RepoRoot ".venv-win/Scripts/python.exe"),
        (Join-Path $RepoRoot ".venv/Scripts/python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py"
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    throw "[zed_task] No project Python found. Run: .\scripts\engineering\dev\setup_env_windows.ps1"
}

# Strip a leading "--" separator if present (Zed/shell ergonomics).
if ($ToolArgs -and $ToolArgs.Count -gt 0 -and $ToolArgs[0] -eq "--") {
    if ($ToolArgs.Count -eq 1) {
        $ToolArgs = @()
    } else {
        $ToolArgs = $ToolArgs[1..($ToolArgs.Count - 1)]
    }
}

$Python = Get-ProjectPython
if (Test-Path (Join-Path $RepoRoot ".venv-win")) {
    $env:VIRTUAL_ENV = (Join-Path $RepoRoot ".venv-win")
}
$env:PYTHONDONTWRITEBYTECODE = "1"
if (-not $env:VCR_RECORD_MODE) {
    $env:VCR_RECORD_MODE = "none"
}

if ($Module) {
    if ($Python -eq "py") {
        & py -3 -m $Module @ToolArgs
    } else {
        & $Python -m $Module @ToolArgs
    }
    exit $LASTEXITCODE
}

if ($Script) {
    $ScriptPath = if ([System.IO.Path]::IsPathRooted($Script)) {
        $Script
    } else {
        Join-Path $RepoRoot $Script
    }
    if (-not (Test-Path $ScriptPath)) {
        throw "[zed_task] Script not found: $ScriptPath"
    }
    if ($Python -eq "py") {
        & py -3 $ScriptPath @ToolArgs
    } else {
        & $Python $ScriptPath @ToolArgs
    }
    exit $LASTEXITCODE
}

if ($Exe) {
    $ScriptsDir = Join-Path $RepoRoot ".venv-win/Scripts"
    $ExePath = Join-Path $ScriptsDir ($Exe + ".exe")
    if (-not (Test-Path $ExePath)) {
        $ExePath = Join-Path $ScriptsDir $Exe
    }
    if (-not (Test-Path $ExePath)) {
        throw "[zed_task] Executable not found in .venv-win/Scripts: $Exe"
    }
    & $ExePath @ToolArgs
    exit $LASTEXITCODE
}

Write-Error "[zed_task] Provide -Module, -Script, or -Exe."
exit 2
