# Compatibility adapter for the canonical fail-closed Docker runtime manager.
param(
    [Parameter(Position = 0)][string]$Command = "help",
    [Parameter(Position = 1)][string]$Argument = "",
    [Parameter(Position = 2)][string]$Confirmation = "",
    [string]$Mode = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Manager = Join-Path $ProjectRoot "scripts/ops/runtime/docker/runtime_manager.py"
$GrafanaPreflight = Join-Path $ProjectRoot "scripts/ops/observability/grafana/check_grafana_dashboard_audit_preflight.py"
$RepoEnvLoader = Join-Path $ProjectRoot "scripts/ai/mcp/support/load_repo_env.ps1"

# Import the repository environment into this process only. The shared loader
# preserves already-set process values and owns all supported aliases.
if (-not $env:BIOETL_SKIP_ENV_LOCAL) {
    $env:BIOETL_SKIP_ENV_LOCAL = "1"
}
. $RepoEnvLoader
Import-BioetlRepoEnv -RepoRoot $ProjectRoot

function Get-PythonCommand {
    if ($env:BIOETL_PYTHON -and (Get-Command $env:BIOETL_PYTHON -ErrorAction SilentlyContinue)) {
        return $env:BIOETL_PYTHON
    }
    $ProjectPython = Join-Path $ProjectRoot ".venv-win/Scripts/python.exe"
    if (Test-Path $ProjectPython) {
        return $ProjectPython
    }
    foreach ($Candidate in @("python3", "python")) {
        if (Get-Command $Candidate -ErrorAction SilentlyContinue) { return $Candidate }
    }
    throw "Python is required for Docker lifecycle management."
}

function Invoke-Manager {
    param([string[]]$ManagerArgs)
    $Python = Get-PythonCommand
    & $Python $Manager @ManagerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker runtime manager failed with exit code $LASTEXITCODE." }
}

function Invoke-GrafanaPreflight {
    $Python = Get-PythonCommand
    & $Python $GrafanaPreflight --json
    if ($LASTEXITCODE -ne 0) { throw "Grafana audit preflight failed with exit code $LASTEXITCODE." }
}

function Invoke-ForStacks {
    param([string]$Action, [string[]]$Stacks)
    $Failures = @()
    foreach ($Stack in $Stacks) {
        try { Invoke-Manager -ManagerArgs @($Action, "--stack", $Stack) }
        catch { $Failures += $Stack; Write-Error $_ -ErrorAction Continue }
    }
    if ($Failures.Count -gt 0) { throw "Docker action failed for stacks: $($Failures -join ', ')." }
}

function Show-Usage {
    @"
Usage: scripts/ops/docker-setup.ps1 <command> [argument]

Commands: check, ensure-networks, start, recover, start-full, monitoring,
          stop, stop-full, status, health, diagnose, logs,
          grafana-preflight, clean, help

clean requires the literal third argument CLEAN. Volumes and images are retained.
Repository .env values are loaded into this process through the shared loader;
already-set process values take precedence and no env file is modified.
"@
}

if ($Mode) { $Command = $Mode }
$Stack = if ($Argument) { $Argument } else { "main" }
switch ($Command) {
    "check" { Invoke-Manager -ManagerArgs @("check", "--stack", $Stack) }
    "ensure-networks" { Invoke-Manager -ManagerArgs @("ensure-networks", "--stack", $Stack, "--timeout", "30") }
    "start" { Invoke-Manager -ManagerArgs @("start", "--stack", $Stack, "--timeout", "180") }
    "basic" { Invoke-Manager -ManagerArgs @("start", "--stack", $Stack) }
    "recover" { Invoke-Manager -ManagerArgs @("recover", "--stack", $Stack, "--timeout", "180") }
    "monitoring" { Invoke-Manager -ManagerArgs @("start", "--stack", "monitoring", "--timeout", "180") }
    "start-full" { Invoke-ForStacks -Action "start" -Stacks @("main", "neo4j", "redis", "minio", "monitoring") }
    "full" { Invoke-ForStacks -Action "start" -Stacks @("main", "neo4j", "redis", "minio", "monitoring") }
    "stop" { Invoke-Manager -ManagerArgs @("stop", "--stack", $Stack) }
    "stop-full" { Invoke-ForStacks -Action "stop" -Stacks @("monitoring", "minio", "redis", "neo4j", "main") }
    "status" { Invoke-Manager -ManagerArgs @("status", "--stack", $Stack) }
    "health" { Invoke-Manager -ManagerArgs @("status", "--stack", "main") }
    "diagnose" { Invoke-Manager -ManagerArgs @("diagnose", "--stack", $Stack) }
    "logs" { Invoke-Manager -ManagerArgs @("logs", "--stack", $Stack) }
    "grafana-preflight" { Invoke-GrafanaPreflight }
    "clean" { Invoke-Manager -ManagerArgs @("clean", "--stack", $Stack, "--confirm-destructive", $Confirmation) }
    { $_ -in @("help", "--help", "-h", "") } { Show-Usage }
    default { Show-Usage; throw "Unknown command: $Command" }
}
