[CmdletBinding()]
param(
    [int]$Port = 8081,
    [switch]$Json,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Show-Usage {
    @"
Usage:
  powershell -ExecutionPolicy Bypass -File scripts/ops/observability/grafana/start_quarantine_explorer.ps1

Ensures bioetl quarantine serve is listening on port 8081 for Grafana ID / Processed Records panels.

Options:
  -Port <int>   Backend port (default: 8081)
  -Json         Emit JSON status on stdout
  -Help         Show this help
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\..\.."))

$PythonCommand = $null
foreach ($Candidate in @(
        (Join-Path $RepoRoot ".venv-win\Scripts\python.exe"),
        (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
        "python"
    )) {
    if ($Candidate -eq "python") {
        $Resolved = Get-Command python -ErrorAction SilentlyContinue
        if ($null -ne $Resolved) {
            $PythonCommand = $Resolved.Source
            break
        }
        continue
    }
    if (Test-Path -LiteralPath $Candidate) {
        $PythonCommand = $Candidate
        break
    }
}

if (-not $PythonCommand) {
    throw "Python executable not found. Install Python or create .venv-win under the repo root."
}

$Arguments = @(
    "-m", "scripts.ops", "ensure-quarantine-explorer",
    "--port", "$Port"
)
if ($Json) {
    $Arguments += "--json"
}

Push-Location $RepoRoot
try {
    $env:PYTHONPATH = Join-Path $RepoRoot "src"
    & $PythonCommand @Arguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
