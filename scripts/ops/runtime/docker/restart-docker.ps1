#!/usr/bin/env pwsh
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$ConfirmLastResort,
    [ValidateRange(10, 180)] [int]$TimeoutSeconds = 180,
    [string]$ReportPath = "reports/quality/docker-desktop-recovery.json"
)

$ErrorActionPreference = 'Stop'
$Started = Get-Date
$Deadline = $Started.AddSeconds($TimeoutSeconds)
$Observations = [System.Collections.Generic.List[object]]::new()

function Invoke-BoundedCommand {
    param([string]$Name, [string[]]$Arguments)
    try {
        $Output = & $Name @Arguments 2>&1 | Out-String
        $Code = $LASTEXITCODE
    } catch {
        $Output = $_.Exception.Message
        $Code = 127
    }
    $Output = $Output -replace '(?i)gh[pousr]_[A-Za-z0-9_]{12,}', '<redacted>'
    $Output = $Output -replace '(?i)([A-Za-z0-9_]*(?:password|secret|token|credential|auth)[A-Za-z0-9_]*)=[^\s,;]+', '$1=<redacted>'
    $Output = $Output -replace '(://)[^/@\s:]+:[^/@\s]+@', '$1<redacted>:<redacted>@'
    if ($Output.Length -gt 4000) { $Output = $Output.Substring(0, 4000) }
    $Row = [ordered]@{ command = @($Name) + $Arguments; returncode = $Code; output = $Output }
    $Observations.Add($Row)
    return $Row
}

function Test-DockerReady {
    $Row = Invoke-BoundedCommand 'docker' @('info', '--format', '{{json .ServerVersion}}')
    return ($Row.returncode -eq 0)
}

function Test-DesktopCapability {
    param([string]$Command)
    $Row = Invoke-BoundedCommand 'docker' @('desktop', $Command, '--help')
    return ($Row.returncode -eq 0)
}

function Write-RecoveryReport {
    param([string]$Cause, [bool]$Ok, [string[]]$Actions)
    $Target = [System.IO.Path]::GetFullPath($ReportPath)
    [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($Target)) | Out-Null
    $Payload = [ordered]@{
        schema_version = 'bioetl-docker-desktop-recovery-v1'
        generated_at = (Get-Date).ToUniversalTime().ToString('o')
        ok = $Ok
        primary_cause = $Cause
        actions = $Actions
        elapsed_seconds = [math]::Round(((Get-Date) - $Started).TotalSeconds, 3)
        observations = $Observations
        redaction_applied = $true
        last_resort_confirmed = [bool]$ConfirmLastResort
    }
    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Target -Encoding utf8
}

$Actions = [System.Collections.Generic.List[string]]::new()
if (Test-DockerReady) {
    Write-RecoveryReport 'none' $true @('already_ready')
    Write-Output 'Docker daemon is already ready'
    exit 0
}

# Evidence first. Every command is read-only and bounded by captured output.
foreach ($DesktopCommand in @('status', 'logs', 'diagnose')) {
    if (Test-DesktopCapability $DesktopCommand) {
        Invoke-BoundedCommand 'docker' @('desktop', $DesktopCommand) | Out-Null
    }
}
Invoke-BoundedCommand 'docker' @('compose', 'ls', '--all', '--format', 'json') | Out-Null
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    Invoke-BoundedCommand 'wsl.exe' @('--status') | Out-Null
    Invoke-BoundedCommand 'wsl.exe' @('--list', '--verbose') | Out-Null
}

$RestartSupported = Test-DesktopCapability 'restart'
if ($RestartSupported) {
    $Restart = Invoke-BoundedCommand 'docker' @('desktop', 'restart')
    $Actions.Add('docker_desktop_restart')
    if ($Restart.returncode -ne 0) {
        Write-RecoveryReport 'desktop_restart_failed' $false $Actions
        exit 1
    }
} else {
    $DockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $DockerDesktop)) {
        Write-RecoveryReport 'desktop_cli_unavailable' $false $Actions
        throw "Docker Desktop CLI restart is unavailable and executable was not found"
    }
    Start-Process -FilePath $DockerDesktop
    $Actions.Add('desktop_normal_launch_fallback')
}

while ((Get-Date) -lt $Deadline) {
    if (Test-DockerReady) {
        Write-RecoveryReport 'none' $true $Actions
        Write-Output 'Docker daemon recovered within the bounded deadline'
        exit 0
    }
    Start-Sleep -Seconds 2
}

Write-RecoveryReport 'desktop_recovery_timeout' $false $Actions
if ($ConfirmLastResort) {
    $Desktop = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
    if ($Desktop -and $PSCmdlet.ShouldProcess('Docker Desktop', 'force terminate as confirmed last resort')) {
        $Desktop | Stop-Process -Force
        throw 'Confirmed last-resort termination completed; rerun bounded recovery after reviewing the report. WSL was not shut down.'
    }
}
throw "Docker Desktop did not recover within $TimeoutSeconds seconds; no force-kill or WSL shutdown was performed"
