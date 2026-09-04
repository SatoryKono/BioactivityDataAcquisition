#Requires -Version 5.1
<#
.SYNOPSIS
  Host-side hardening so Docker Desktop/WSL stops flapping on 32 GiB Windows.

.DESCRIPTION
  Machine-local only (not committed secrets):
    1) Ensure %USERPROFILE%\.wslconfig caps WSL at 6 GiB (host headroom).
    2) Patch %APPDATA%\Docker\settings-store.json:
       - Resource Saver effectively off (huge AutoPauseTimeoutSeconds)
       - AutoStart on
       - Extensions / Docker AI / inference off (less backend thrash)
    3) Optionally register a logon + periodic watchdog task that re-runs
       ensure-stable when the engine pipe dies.

.EXAMPLE
  .\scripts\ops\runtime\docker\harden-desktop-host.ps1 -RegisterWatchdog
#>
[CmdletBinding()]
param(
    [switch]$RegisterWatchdog,
    [switch]$UnregisterWatchdog,
    [int]$WatchdogMinutes = 5,
    [int]$WslMemoryGb = 6
)

$ErrorActionPreference = 'Stop'
$InformationPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$TaskName = 'BioETL-Docker-Stable-Watchdog'
$WslConfigPath = Join-Path $env:USERPROFILE '.wslconfig'
$SettingsPath = Join-Path $env:APPDATA 'Docker\settings-store.json'
$EnsureScript = Join-Path $Root 'scripts\ops\runtime\docker\ensure-stable.ps1'
$WatchdogScript = Join-Path $Root 'scripts\ops\runtime\docker\watchdog-docker-stable.ps1'

function Write-WslConfig {
    param([int]$MemoryGb)
    $desired = @"
[wsl2]
# BioETL host hardening (32 GiB class): keep Windows free RAM so docker-desktop
# does not flap under PyCharm + Docker co-tenancy. Do not raise above 6 without
# measuring free host RAM under IDE load.
memory=${MemoryGb}GB
swap=4GB
processors=4
dnsProxy=true
localhostForwarding=true
kernelCommandLine=sysctl.vm.swappiness=10 sysctl.vm.overcommit_memory=1

[experimental]
bestEffortDnsParsing=true
autoMemoryReclaim=gradual
"@
    $current = if (Test-Path $WslConfigPath) { Get-Content $WslConfigPath -Raw } else { '' }
    if ($current.Trim() -eq $desired.Trim()) {
        Write-Information "WSL config already hardened: $WslConfigPath"
        return $false
    }
    if (Test-Path $WslConfigPath) {
        $bak = "$WslConfigPath.bak-bioetl-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $WslConfigPath $bak -Force
        Write-Information "Backed up previous .wslconfig -> $bak"
    }
    Set-Content -Path $WslConfigPath -Value $desired.TrimEnd() -Encoding UTF8
    Write-Information "Wrote hardened .wslconfig (memory=${MemoryGb}GB). Applies after next wsl --shutdown / Desktop restart."
    return $true
}

function Write-DockerSettings {
    $dir = Split-Path $SettingsPath -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $obj = [ordered]@{}
    if (Test-Path $SettingsPath) {
        $raw = Get-Content $SettingsPath -Raw -ErrorAction SilentlyContinue
        if ($raw) {
            $parsed = $raw | ConvertFrom-Json
            foreach ($p in $parsed.PSObject.Properties) {
                $obj[$p.Name] = $p.Value
            }
        }
    }

    # Resource Saver: on WSL it pauses the engine when idle. Keep it effectively
    # disabled so npipe dockerDesktopLinuxEngine does not disappear mid-session.
    # Docs: autoPauseTimeoutSeconds in settings-store.json (must be > 30).
    $desired = @{
        AutoPauseTimeoutSeconds              = 604800  # 7 days
        AutoStart                            = $true
        KubernetesEnabled                    = $false
        ExtensionsEnabled                    = $false
        EnableDockerAI                       = $false
        EnableIntegrationWithDefaultWslDistro = $true
        UseContainerdSnapshotter             = $true
        enableInference                      = $false
        enableInferenceGPUVariant            = $false
        useBackgroundIndexing                = $false
        ShowExtensionsSystemContainers       = $false
    }

    $needsWrite = $false
    foreach ($k in $desired.Keys) {
        $cur = $obj[$k]
        $want = $desired[$k]
        if ($null -eq $cur -or ([string]$cur -ne [string]$want)) {
            $needsWrite = $true
            break
        }
    }
    if (-not $needsWrite) {
        Write-Information "Docker settings already hardened: $SettingsPath"
        return
    }

    if (Test-Path $SettingsPath) {
        $bak = "$SettingsPath.bak-bioetl-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $SettingsPath $bak -Force
        Write-Information "Backed up settings-store.json -> $bak"
    }
    foreach ($k in $desired.Keys) {
        $obj[$k] = $desired[$k]
    }

    $json = $obj | ConvertTo-Json -Depth 12
    Set-Content -Path $SettingsPath -Value $json -Encoding UTF8
    Write-Information "Hardened Docker Desktop settings-store.json"
    Write-Information "  AutoPauseTimeoutSeconds=604800 (Resource Saver effectively off)"
    Write-Information "  AutoStart=true; Extensions/AI/inference=false; Kubernetes=false"
}

function Unregister-WatchdogTask {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Information "Removed scheduled task: $TaskName"
    } else {
        Write-Information "No scheduled task named $TaskName"
    }
}

function Register-WatchdogTask {
    param([int]$Minutes)
    if (-not (Test-Path $WatchdogScript)) {
        throw "Missing watchdog script: $WatchdogScript"
    }
    if (-not (Test-Path $EnsureScript)) {
        throw "Missing ensure-stable script: $EnsureScript"
    }

    Unregister-WatchdogTask | Out-Null

    $arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatchdogScript`" -WithNeo4j"
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg -WorkingDirectory $Root
    $t1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    # Repetition: start shortly after registration, every N minutes indefinitely.
    $t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
        -RepetitionInterval (New-TimeSpan -Minutes $Minutes) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($t1, $t2) `
        -Settings $settings -Principal $principal -Force | Out-Null
    Write-Information "Registered scheduled task: $TaskName (every ${Minutes}m + at logon)"
    Write-Information "  Runs: $WatchdogScript -WithNeo4j"
}

# --- main ---
Write-Host "=== BioETL Docker Desktop host harden ==="
Write-Host "Repo: $Root"
$wslChanged = Write-WslConfig -MemoryGb $WslMemoryGb
Write-DockerSettings

if ($UnregisterWatchdog) {
    Unregister-WatchdogTask
}
if ($RegisterWatchdog) {
    Register-WatchdogTask -Minutes $WatchdogMinutes
}

Write-Host ""
Write-Host "Next:"
Write-Host "  1) .\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j"
if ($wslChanged) {
    Write-Host "  2) .wslconfig changed - if engine still flaps: ensure-stable.ps1 -RestartWsl -WithNeo4j"
}
Write-Host "  3) Optional UI: Docker Desktop Settings > Resources > Resource Saver OFF"
if (-not $RegisterWatchdog -and -not $UnregisterWatchdog) {
    Write-Host "  4) Auto-recover: re-run this script with -RegisterWatchdog"
}
