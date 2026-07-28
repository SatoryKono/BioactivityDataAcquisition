#Requires -Version 5.1
<#
.SYNOPSIS
  Lightweight auto-recovery for Docker Desktop engine flaps (BioETL default stack).

.DESCRIPTION
  Safe for Task Scheduler every few minutes:
    - If engine is healthy and bioetl (+ optional neo4j) are running → exit 0.
    - If engine dead → free-RAM gate → ensure-stable -RestartWsl -WithNeo4j (rate-limited).
    - If engine OK but containers missing → ensure-stable -WithNeo4j (no WSL restart).
  Never prune, never down -v, never force-recreate thrash.

.EXAMPLE
  .\scripts\ops\runtime\docker\watchdog-docker-stable.ps1 -WithNeo4j

.NOTES
  Default state/log directory is reports\logs\docker-watchdog (gitignored under
  reports/logs/*) so the watchdog does not recreate root logs/. Override with
  -StateDir when needed. Root logs/ remains non-retained per file-policy §0.
#>
[CmdletBinding()]
param(
    [switch]$WithNeo4j,
    [int]$MinFreeGbForHardRestart = 3,
    [int]$MinSecondsBetweenHardRestarts = 600,
    [string]$StateDir = ''
)

$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location $Root
if (-not $StateDir) {
    # RH4-02 / #6816: do not default to root logs/ (re-clutters exact root).
    $StateDir = Join-Path $Root 'reports\logs\docker-watchdog'
}
if (-not (Test-Path $StateDir)) {
    New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
}
$LogPath = Join-Path $StateDir 'watchdog.log'
$StatePath = Join-Path $StateDir 'state.json'
$EnsureScript = Join-Path $Root 'scripts\ops\runtime\docker\ensure-stable.ps1'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = '{0:u} [{1}] {2}' -f (Get-Date).ToUniversalTime(), $Level, $Message
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-HostFreeGb {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round($os.FreePhysicalMemory / 1MB, 1)
}

function Test-EngineUp {
    $ver = docker info --format '{{.ServerVersion}}' 2>$null
    return ($LASTEXITCODE -eq 0 -and $ver)
}

function Test-ContainerRunning {
    param([string]$Name)
    $st = docker inspect --format '{{.State.Running}}' $Name 2>$null
    return ($LASTEXITCODE -eq 0 -and $st -eq 'true')
}

function Get-State {
    if (Test-Path $StatePath) {
        try { return Get-Content $StatePath -Raw | ConvertFrom-Json } catch { }
    }
    return [pscustomobject]@{ lastHardRestartUnix = 0 }
}

function Save-State {
    param($State)
    ($State | ConvertTo-Json) | Set-Content -Path $StatePath -Encoding UTF8
}

function Invoke-Ensure {
    param([switch]$RestartWsl)
    # Do not stream child stdout into this function's return value (PowerShell
    # aggregates pipeline output). Capture exit code via Start-Process.
    $argList = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $EnsureScript,
        '-SkipHostHarden'
    )
    if ($RestartWsl) { $argList += '-RestartWsl' }
    if ($WithNeo4j) { $argList += '-WithNeo4j' }
    Write-Log "Invoking ensure-stable RestartWsl=$RestartWsl WithNeo4j=$WithNeo4j"
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList `
        -WorkingDirectory $Root -Wait -PassThru -NoNewWindow
    return [int]$p.ExitCode
}

# --- main ---
$free = Get-HostFreeGb
$engine = Test-EngineUp
$bioetl = $false
$neo4j = $false
if ($engine) {
    $bioetl = Test-ContainerRunning 'bioetl'
    if ($WithNeo4j) { $neo4j = Test-ContainerRunning 'bioetl-neo4j' }
}

if ($engine -and $bioetl -and ((-not $WithNeo4j) -or $neo4j)) {
    Write-Log "OK engine+stacks free=${free}GiB"
    exit 0
}

if ($engine -and (-not $bioetl -or ($WithNeo4j -and -not $neo4j))) {
    Write-Log "Engine up but stack incomplete (bioetl=$bioetl neo4j=$neo4j); soft ensure"
    $code = Invoke-Ensure
    exit $code
}

# Engine down
Write-Log "ENGINE DOWN free=${free}GiB" 'WARN'
$state = Get-State
$now = [int][double]::Parse((Get-Date -UFormat %s))
$since = $now - [int]$state.lastHardRestartUnix
if ($since -lt $MinSecondsBetweenHardRestarts -and [int]$state.lastHardRestartUnix -gt 0) {
    Write-Log "Hard restart rate-limited (${since}s < ${MinSecondsBetweenHardRestarts}s); skip" 'WARN'
    exit 3
}
if ($free -lt $MinFreeGbForHardRestart) {
    Write-Log "Free RAM ${free}GiB < ${MinFreeGbForHardRestart}GiB; refuse hard restart (close IDE/browsers)" 'ERROR'
    exit 2
}

$code = Invoke-Ensure -RestartWsl
$state = [pscustomobject]@{ lastHardRestartUnix = $now; lastExit = $code; freeGb = $free }
Save-State $state
if ($code -eq 0) {
    Write-Log 'Recovered via ensure-stable -RestartWsl'
} else {
    Write-Log "ensure-stable failed exit=$code" 'ERROR'
}
exit $code
