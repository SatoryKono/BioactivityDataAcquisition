#!/usr/bin/env pwsh
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [switch]$ConfirmLastResort,
    [string]$LastResortConfirmation = '',
    [ValidateRange(10, 180)] [int]$TimeoutSeconds = 180,
    [ValidateRange(1, 60)] [int]$CommandTimeoutSeconds = 15,
    [string]$ReportPath = "reports/quality/docker-desktop-recovery.json"
)

$ErrorActionPreference = 'Stop'
$Started = Get-Date
$RecoveryDeadline = $Started.AddSeconds($TimeoutSeconds)
$Observations = [System.Collections.Generic.List[object]]::new()
$Actions = [System.Collections.Generic.List[string]]::new()
$LastResortToken = 'I_UNDERSTAND_FORCE_TERMINATION_IS_DESTRUCTIVE'
$Diagnostics = [ordered]@{
    desktop = [ordered]@{}
    daemon_identity = [ordered]@{}
    wsl_integration = [ordered]@{}
    engine_topology = [ordered]@{}
    vhd_attachment = [ordered]@{}
    project_origins = [ordered]@{}
    port_owners = [ordered]@{}
    bind_path_translation = [ordered]@{}
    data_capacity = [ordered]@{}
}

function Protect-SensitiveString {
    param([AllowNull()] [string]$Value)

    if ($null -eq $Value) { return $null }
    $Protected = $Value
    $Protected = $Protected -replace '(?i)gh[pousr]_[A-Za-z0-9_]{12,}', '<redacted>'
    $Protected = $Protected -replace '(?i)(authorization\s*[:=]\s*(?:bearer|basic)\s+)[^\s,;]+', '$1<redacted>'
    $Protected = $Protected -replace '(?i)(--?(?:password|secret|token|credential|auth)(?:=|\s+))[^\s,;]+', '$1<redacted>'
    $Protected = $Protected -replace '(?i)([A-Za-z0-9_]*(?:password|secret|token|credential|auth)[A-Za-z0-9_]*)=[^\s,;]+', '$1=<redacted>'
    $Protected = $Protected -replace '(?i)("(?:password|secret|token|credential|authorization)"\s*:\s*")[^"]*', '$1<redacted>'
    $Protected = $Protected -replace '(://)[^/@\s:]+:[^/@\s]+@', '$1<redacted>:<redacted>@'
    $Protected = $Protected -replace '(?i)(C:\\Users\\)[^\\\s]+', '$1<user>'
    $Protected = $Protected -replace '(/home/)[^/\s]+', '$1<user>'
    return $Protected
}

function Test-SensitiveKeyName {
    param([string]$Name)

    return (
        $Name -match '(?i)(password|secret|credential|authorization|(?<![a-z])auth(?![a-z]))' -or
        (
            $Name -match '(?i)token' -and
            $Name -notmatch '(?i)(valid|enabled|present|count|requested)$'
        )
    )
}

function Protect-SensitiveDictionary {
    param([System.Collections.IDictionary]$Value)

    $Protected = [ordered]@{}
    foreach ($Key in $Value.Keys) {
        $SafeKey = Protect-SensitiveString ([string]$Key)
        # Redact secret-bearing keys, but keep boolean/metadata flags such as
        # last_resort_token_valid that only embed the word "token".
        if (Test-SensitiveKeyName -Name $SafeKey) {
            $Protected[$SafeKey] = '<redacted>'
        } else {
            $Protected[$SafeKey] = Protect-SensitiveValue $Value[$Key]
        }
    }
    return $Protected
}

function Protect-SensitiveObject {
    param([pscustomobject]$Value)

    $Protected = [ordered]@{}
    foreach ($Property in $Value.PSObject.Properties) {
        $SafeName = Protect-SensitiveString $Property.Name
        if (Test-SensitiveKeyName -Name $SafeName) {
            $Protected[$SafeName] = '<redacted>'
        } else {
            $Protected[$SafeName] = Protect-SensitiveValue $Property.Value
        }
    }
    return $Protected
}

function Protect-SensitiveEnumerable {
    param([System.Collections.IEnumerable]$Value)

    $ProtectedItems = [System.Collections.Generic.List[object]]::new()
    foreach ($Item in $Value) {
        [void]$ProtectedItems.Add((Protect-SensitiveValue $Item))
    }
    return ,$ProtectedItems
}

function Protect-SensitiveValue {
    param([AllowNull()] [object]$Value)

    if ($null -eq $Value) { return $null }
    if ($Value -is [string]) { return Protect-SensitiveString $Value }
    if ($Value -is [System.Collections.IDictionary]) {
        return Protect-SensitiveDictionary -Value $Value
    }
    if ($Value -is [pscustomobject]) {
        return Protect-SensitiveObject -Value $Value
    }
    if (($Value -is [System.Collections.IEnumerable]) -and -not ($Value -is [string])) {
        return Protect-SensitiveEnumerable -Value $Value
    }
    return $Value
}

function Get-RemainingMilliseconds {
    $Remaining = [math]::Floor(($RecoveryDeadline - (Get-Date)).TotalMilliseconds)
    return [math]::Max(0, [int]$Remaining)
}

function ConvertTo-ProcessArgument {
    param([AllowEmptyString()] [string]$Argument)

    if ($Argument -notmatch '[\s"]') { return $Argument }
    $Escaped = $Argument -replace '(\\*)"', '$1$1\"'
    $Escaped = $Escaped -replace '(\\+)$', '$1$1'
    return '"' + $Escaped + '"'
}

function ConvertTo-CmdArgument {
    param([AllowEmptyString()] [string]$Argument)

    # cmd.exe parses the whole /c string: expand %VAR%, treat bare |/&/<> as
    # operators, and uses doubled quotes for literals inside a quoted token.
    $Escaped = $Argument -replace '%', '%%'
    $Escaped = $Escaped -replace '"', '""'
    if ($Escaped -match '[\s"&|<>^]') {
        return '"' + $Escaped + '"'
    }
    return $Escaped
}

function Resolve-BoundedCommandPath {
    param([Parameter(Mandatory)] [string]$Name)

    # Prefer an explicit on-PATH application (including PATHEXT .cmd/.bat shims).
    # ProcessStartInfo without a shell does not reliably execute extensionless
    # POSIX shims on Windows, and a bare FileName like "docker" may miss .cmd.
    $Candidates = @(
        Get-Command $Name -All -ErrorAction SilentlyContinue
        if ($Name -notlike '*.exe') {
            Get-Command ($Name + '.exe') -All -ErrorAction SilentlyContinue
        }
        if ($Name -like '*.exe') {
            $Base = [System.IO.Path]::GetFileNameWithoutExtension($Name)
            Get-Command $Base -All -ErrorAction SilentlyContinue
            Get-Command ($Base + '.cmd') -All -ErrorAction SilentlyContinue
            Get-Command ($Base + '.bat') -All -ErrorAction SilentlyContinue
        }
    ) | Where-Object { $null -ne $_ }

    foreach ($Candidate in $Candidates) {
        if ($Candidate.CommandType -eq 'Application' -and -not [string]::IsNullOrWhiteSpace($Candidate.Source)) {
            return $Candidate.Source
        }
        if ($Candidate.CommandType -eq 'ExternalScript' -and -not [string]::IsNullOrWhiteSpace($Candidate.Source)) {
            return $Candidate.Source
        }
    }
    return $Name
}

function New-BoundedProcessStartInfo {
    param(
        [Parameter(Mandatory)] [string]$ResolvedName,
        [string[]]$Arguments = @()
    )

    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    # .cmd/.bat shims need a shell on Windows; PE apps do not.
    # Arguments must use cmd-specific quoting (not PE argv rules): bare
    # pipes in docker --format templates would otherwise split the line.
    $IsShellScript = $ResolvedName -match '\.(cmd|bat)$'
    if ($IsShellScript) {
        $StartInfo.FileName = $env:ComSpec
        if ([string]::IsNullOrWhiteSpace($StartInfo.FileName)) {
            $StartInfo.FileName = 'cmd.exe'
        }
        $QuotedArgs = @(
            $Arguments | ForEach-Object { ConvertTo-CmdArgument $_ }
        ) -join ' '
        $StartInfo.Arguments = '/d /c ' + (ConvertTo-CmdArgument $ResolvedName) + $(
            if ($QuotedArgs) { ' ' + $QuotedArgs } else { '' }
        )
        $StartInfo.UseShellExecute = $false
    } else {
        $StartInfo.FileName = $ResolvedName
        $StartInfo.UseShellExecute = $false
        if ($StartInfo.PSObject.Properties.Name -contains 'ArgumentList') {
            foreach ($Argument in $Arguments) {
                [void]$StartInfo.ArgumentList.Add($Argument)
            }
        } else {
            $StartInfo.Arguments = @(
                $Arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }
            ) -join ' '
        }
    }
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.CreateNoWindow = $true
    return $StartInfo
}

function Stop-BoundedProcessTree {
    param([int]$ProcessId)

    if ($ProcessId -le 0) { return }
    try {
        $Killer = [System.Diagnostics.Process]::new()
        $KillInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $KillInfo.FileName = 'taskkill.exe'
        $KillInfo.Arguments = "/F /T /PID $ProcessId"
        $KillInfo.UseShellExecute = $false
        $KillInfo.CreateNoWindow = $true
        $KillInfo.RedirectStandardOutput = $true
        $KillInfo.RedirectStandardError = $true
        $Killer.StartInfo = $KillInfo
        [void]$Killer.Start()
        [void]$Killer.WaitForExit(2000)
        $Killer.Dispose()
    } catch {
        Write-Verbose "taskkill tree cleanup failed for pid ${ProcessId}: $($_.Exception.Message)"
    }
}

function Invoke-BoundedProcess {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$ResolvedName,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory)] [int]$WaitMilliseconds
    )

    $Code = 127
    $TimedOut = $false
    $Output = ''
    $Process = [System.Diagnostics.Process]::new()
    try {
        $Process.StartInfo = New-BoundedProcessStartInfo -ResolvedName $ResolvedName -Arguments $Arguments
        if (-not $Process.Start()) { throw "Unable to start $Name" }
        $StdOutTask = $Process.StandardOutput.ReadToEndAsync()
        $StdErrTask = $Process.StandardError.ReadToEndAsync()
        if (-not $Process.WaitForExit($WaitMilliseconds)) {
            $TimedOut = $true
            $Code = 124
            $ProcessId = $Process.Id
            try {
                $Process.Kill($true)
            } catch {
                Write-Verbose "Process.Kill failed for pid ${ProcessId}: $($_.Exception.Message)"
            }
            # Ensure cmd.exe child trees (python sleep fakes) do not outlive
            # the bounded command deadline on Windows.
            Stop-BoundedProcessTree -ProcessId $ProcessId
            [void]$Process.WaitForExit(2000)
        } else {
            $Code = $Process.ExitCode
        }
        if ($Process.HasExited) {
            $StdOut = $StdOutTask.GetAwaiter().GetResult()
            $StdErr = $StdErrTask.GetAwaiter().GetResult()
            $Output = @($StdOut, $StdErr) -join [Environment]::NewLine
        } else {
            $Output = 'Command exceeded its deadline and output capture did not complete.'
        }
    } catch {
        $Output = $_.Exception.Message
        $Code = 127
    } finally {
        $Process.Dispose()
    }
    return [ordered]@{
        returncode = $Code
        timed_out = $TimedOut
        output = $Output
    }
}

function Invoke-BoundedCommand {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [string[]]$Arguments = @(),
        # Desktop recovery actions (restart/stop/start) must still receive a full
        # command budget after diagnostics have nearly exhausted the global
        # TimeoutSeconds window; otherwise stop/start fallback is a no-op timeout.
        [switch]$AllowOverrun
    )

    $CommandStarted = Get-Date
    $RemainingMilliseconds = Get-RemainingMilliseconds
    $WaitMilliseconds = if ($AllowOverrun) {
        $CommandTimeoutSeconds * 1000
    } else {
        [math]::Min($CommandTimeoutSeconds * 1000, $RemainingMilliseconds)
    }
    $ResolvedName = Resolve-BoundedCommandPath -Name $Name

    if ($WaitMilliseconds -le 0) {
        $Result = [ordered]@{
            returncode = 124
            timed_out = $true
            output = 'Global recovery deadline was exhausted before command start.'
        }
    } else {
        $Result = Invoke-BoundedProcess `
            -Name $Name `
            -ResolvedName $ResolvedName `
            -Arguments $Arguments `
            -WaitMilliseconds $WaitMilliseconds
    }

    $Output = Protect-SensitiveString ([string]$Result.output)
    if ($Output.Length -gt 8000) { $Output = $Output.Substring(0, 8000) }
    $Row = [ordered]@{
        command = Protect-SensitiveValue (@($Name) + $Arguments)
        returncode = $Result.returncode
        timed_out = $Result.timed_out
        duration_seconds = [math]::Round(((Get-Date) - $CommandStarted).TotalSeconds, 3)
        output = $Output
    }
    $Observations.Add($Row)
    return $Row
}

function Test-DockerReady {
    param(
        # Post-action readiness must still be observable after Collect-Diagnostics
        # has nearly exhausted the global TimeoutSeconds window; otherwise a
        # successful desktop restart that already flipped readiness is reported
        # as a timeout solely because the wait budget is empty.
        [switch]$AllowOverrun
    )

    $Row = Invoke-BoundedCommand 'docker' @('info', '--format', '{{json .ServerVersion}}') -AllowOverrun:$AllowOverrun
    return (($Row.returncode -eq 0) -and -not $Row.timed_out)
}

function Test-DesktopCapability {
    param([Parameter(Mandatory)] [string]$Command)

    # Capability probes are metadata-only and must not be starved by the
    # global recovery wait budget consumed during Collect-Diagnostics.
    $Row = Invoke-BoundedCommand 'docker' @('desktop', $Command, '--help') -AllowOverrun
    return (($Row.returncode -eq 0) -and -not $Row.timed_out)
}

function ConvertFrom-JsonLines {
    param([AllowNull()] [string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) { return @() }
    try {
        $Parsed = $Text | ConvertFrom-Json -ErrorAction Stop
        return @($Parsed)
    } catch {
        $Rows = [System.Collections.Generic.List[object]]::new()
        foreach ($Line in ($Text -split "`r?`n")) {
            if ([string]::IsNullOrWhiteSpace($Line)) { continue }
            try {
                $Rows.Add(($Line | ConvertFrom-Json -ErrorAction Stop))
            } catch {
                Write-Verbose "Skipping non-JSON diagnostic line: $($_.Exception.Message)"
            }
        }
        return @($Rows)
    }
}

function Get-CliOrigins {
    $Origins = @(
        @(
            Get-Command docker -All -ErrorAction SilentlyContinue
            Get-Command docker.exe -All -ErrorAction SilentlyContinue
        ) |
            ForEach-Object { $_.Source } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Sort-Object -Unique
    )
    return $Origins
}

function Get-DesktopDiagnosticBundle {
    $Capabilities = [ordered]@{}
    $DesktopRows = [ordered]@{}
    foreach ($DesktopCommand in @('status', 'restart', 'stop', 'start', 'logs', 'diagnose')) {
        $Capabilities[$DesktopCommand] = Test-DesktopCapability $DesktopCommand
    }
    foreach ($DesktopCommand in @('status', 'logs', 'diagnose')) {
        if ($Capabilities[$DesktopCommand]) {
            $DesktopRows[$DesktopCommand] = Invoke-BoundedCommand 'docker' @('desktop', $DesktopCommand) -AllowOverrun
        } else {
            $DesktopRows[$DesktopCommand] = [ordered]@{ returncode = 127; timed_out = $false; output = 'unsupported' }
        }
    }
    $Desktop = [ordered]@{
        capabilities = $Capabilities
        status = if ($DesktopRows.status.returncode -eq 0) { 'available' } elseif ($DesktopRows.status.timed_out) { 'timed_out' } else { 'failed_or_unsupported' }
        status_returncode = $DesktopRows.status.returncode
    }
    return @{ Desktop = $Desktop; Rows = $DesktopRows }
}

function Get-DockerProbeBundle {
    $Version = Invoke-BoundedCommand 'docker' @('version', '--format', '{{json .}}') -AllowOverrun
    $Info = Invoke-BoundedCommand 'docker' @('info', '--format', '{{json .}}') -AllowOverrun
    $ContextShow = Invoke-BoundedCommand 'docker' @('context', 'show') -AllowOverrun
    $ContextList = Invoke-BoundedCommand 'docker' @('context', 'ls', '--format', '{{json .}}') -AllowOverrun
    $Compose = Invoke-BoundedCommand 'docker' @('compose', 'ls', '--all', '--format', 'json') -AllowOverrun
    $Containers = Invoke-BoundedCommand 'docker' @('ps', '--all', '--format', '{{json .}}') -AllowOverrun
    $Mounts = Invoke-BoundedCommand 'docker' @('inspect', '--format', '{{range .Mounts}}{{printf "%s|%s|%s\\n" .Type .Source .Destination}}{{end}}', $(
        @((ConvertFrom-JsonLines $Containers.output) | ForEach-Object { $_.ID } | Where-Object { $_ } | Select-Object -First 200)
    )) -AllowOverrun
    $DiskUsage = Invoke-BoundedCommand 'docker' @('system', 'df', '--format', '{{json .}}') -AllowOverrun
    return @{
        Version = $Version
        Info = $Info
        ContextShow = $ContextShow
        ContextList = $ContextList
        Compose = $Compose
        Containers = $Containers
        Mounts = $Mounts
        DiskUsage = $DiskUsage
    }
}

function Get-LocalEngineProbe {
    if (
        -not [string]::IsNullOrWhiteSpace($env:WSL_DISTRO_NAME) -and
        (Get-Command systemctl -ErrorAction SilentlyContinue)
    ) {
        return Invoke-BoundedCommand 'systemctl' @('is-active', 'docker') -AllowOverrun
    }
    return $null
}

function Get-EngineTopologyDiagnostics {
    param(
        $DesktopRows,
        $Version,
        $Info,
        $LocalEngine,
        $ContextList
    )

    $CliOrigins = @(Get-CliOrigins)
    $Contexts = @(ConvertFrom-JsonLines $ContextList.output)
    $ContextEndpoints = @(
        $Contexts |
            ForEach-Object { @($_.DockerEndpoint, $_.Endpoint, $_.DOCKER_ENDPOINT) } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Sort-Object -Unique
    )
    $DesktopActive = (
        $DesktopRows.status.returncode -eq 0 -and
        $DesktopRows.status.output -match '(?i)\b(running|started)\b'
    ) -or ($Version.returncode -eq 0 -and $Info.returncode -eq 0)
    $LocalEngineActive = $null -ne $LocalEngine -and $LocalEngine.returncode -eq 0 -and $LocalEngine.output.Trim() -eq 'active'
    $classification = if ($DesktopActive -and $LocalEngineActive) {
        'possible_duplicate_active_engines'
    } elseif ($DesktopActive -or $LocalEngineActive) {
        'single_active_engine_observed'
    } else {
        'no_active_engine_observed'
    }
    $cliClass = if ($CliOrigins.Count -gt 1) {
        'multiple_cli_origins'
    } elseif ($CliOrigins.Count -eq 1) {
        'single_cli_origin'
    } else {
        'cli_unavailable'
    }
    return [ordered]@{
        classification = $classification
        cli_origin_classification = $cliClass
        cli_origins = $CliOrigins
        context_endpoints = $ContextEndpoints
        context_endpoint_note = 'Multiple configured contexts do not by themselves prove duplicate active engines.'
        desktop_engine_active = $DesktopActive
        local_wsl_engine_active = $LocalEngineActive
        local_wsl_engine_status = if ($null -eq $LocalEngine) { 'not_checked' } else { $LocalEngine.output.Trim() }
    }
}

function Get-WslDiagnosticBundle {
    # Resolve via the same path logic as Invoke-BoundedCommand so PATHEXT shims
    # (wsl.cmd) used by bounded recovery tests are accepted, not only PE wsl.exe.
    $WslResolved = Resolve-BoundedCommandPath -Name 'wsl.exe'
    $WslAvailable = (
        (Get-Command wsl.exe -ErrorAction SilentlyContinue) -or
        (Get-Command wsl -ErrorAction SilentlyContinue) -or
        (($WslResolved -ne 'wsl.exe') -and (Test-Path -LiteralPath $WslResolved))
    )
    if (-not $WslAvailable) {
        return @{
            Integration = [ordered]@{ classification = 'wsl_cli_unavailable' }
            Status = $null
            List = $null
            DockerDataDf = $null
        }
    }

    $WslStatus = Invoke-BoundedCommand 'wsl.exe' @('--status') -AllowOverrun
    $WslList = Invoke-BoundedCommand 'wsl.exe' @('--list', '--verbose') -AllowOverrun
    $DockerDataDf = Invoke-BoundedCommand 'wsl.exe' @('-d', 'docker-desktop', '--exec', 'df', '-B1', '/var/lib/docker') -AllowOverrun
    $WslText = @($WslStatus.output, $WslList.output) -join "`n"
    $integrationClass = if ($WslList.returncode -ne 0) {
        'query_failed'
    } elseif ($WslText -match '(?i)docker-desktop') {
        'docker_desktop_distribution_present'
    } else {
        'docker_desktop_distribution_not_detected'
    }
    return @{
        Integration = [ordered]@{
            classification = $integrationClass
            status = $WslStatus.output
            distributions = $WslList.output
        }
        Status = $WslStatus
        List = $WslList
        DockerDataDf = $DockerDataDf
    }
}

function Get-VhdAttachmentDiagnostics {
    param($DesktopRows, $WslStatus, $WslList)

    $VhdText = @($DesktopRows.logs.output, $DesktopRows.diagnose.output, $WslStatus.output, $WslList.output) -join "`n"
    $VhdReferences = @(
        [regex]::Matches($VhdText, '(?i)(?:ext4\.vhdx|\.vhdx?\b|docker-desktop-data)') |
            ForEach-Object { $_.Value } |
            Sort-Object -Unique
    )
    $VhdConflicts = @(
        [regex]::Matches($VhdText, '(?i)(?:VHD_ALREADY_ATTACHED|ERROR_SHARING_VIOLATION|already\s+(?:attached|in use)|used by another process|cannot attach[^\r\n]*in use)') |
            ForEach-Object { $_.Value } |
            Sort-Object -Unique
    )
    $classification = if ([string]::IsNullOrWhiteSpace($VhdText)) {
        'unavailable'
    } elseif ($VhdConflicts.Count -gt 0) {
        'attachment_conflict_observed'
    } elseif ($VhdReferences.Count -gt 0) {
        'vhd_reference_observed_no_conflict'
    } else {
        'no_attachment_conflict_observed'
    }
    return [ordered]@{
        classification = $classification
        references = $VhdReferences
        conflict_indicators = $VhdConflicts
    }
}

function Get-ProjectOriginDiagnostics {
    param($Compose)

    $ComposeRows = @(ConvertFrom-JsonLines $Compose.output)
    $Origins = @(
        $ComposeRows |
            ForEach-Object { @($_.ConfigFiles, $_.ConfigFile, $_.config_files) } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Sort-Object -Unique
    )
    $HasWindowsOrigin = @($Origins | Where-Object { $_ -match '^(?:[A-Za-z]:\\|\\\\)' }).Count -gt 0
    $HasLinuxOrigin = @($Origins | Where-Object { $_ -match '^/' }).Count -gt 0
    $classification = if ($Compose.returncode -ne 0) {
        'unavailable'
    } elseif ($Origins.Count -eq 0) {
        'no_projects_observed'
    } elseif ($HasWindowsOrigin -and $HasLinuxOrigin) {
        'mixed_windows_linux_origins'
    } elseif ($HasWindowsOrigin) {
        'windows_origins_observed'
    } elseif ($HasLinuxOrigin) {
        'linux_origins_observed'
    } else {
        'unclassified_origins_observed'
    }
    return [ordered]@{
        classification = $classification
        origins = $Origins
    }
}

function Get-PortOwnerDiagnostics {
    param($Containers)

    $ContainerRows = @(ConvertFrom-JsonLines $Containers.output)
    $PortOwners = [ordered]@{}
    foreach ($Container in $ContainerRows) {
        foreach ($Match in [regex]::Matches([string]$Container.Ports, '(?:(?:0\.0\.0\.0|\[?::\]?):)?(?<port>\d+)->')) {
            $Port = $Match.Groups['port'].Value
            if (-not $PortOwners.Contains($Port)) { $PortOwners[$Port] = @() }
            $PortOwners[$Port] = @(
                (@($PortOwners[$Port]) + @([string]$Container.Names)) |
                    Sort-Object -Unique
            )
        }
    }
    $DuplicatePorts = @($PortOwners.Keys | Where-Object { @($PortOwners[$_]).Count -gt 1 })
    $classification = if ($Containers.returncode -ne 0) {
        'unavailable'
    } elseif ($DuplicatePorts.Count -gt 0) {
        'duplicate_port_owners'
    } else {
        'unique_or_no_published_ports'
    }
    return [ordered]@{
        classification = $classification
        owners = Protect-SensitiveValue $PortOwners
        duplicate_ports = $DuplicatePorts
    }
}

function Get-BindPathDiagnostics {
    param($Mounts)

    $MountText = $Mounts.output
    $classification = if ($Mounts.returncode -ne 0) {
        'unavailable'
    } elseif ($MountText -match '(?i)bind\|[A-Z]:\\') {
        'windows_source_observed'
    } elseif ($MountText -match 'bind\|/(?:mnt|host_mnt)/[a-z]/') {
        'translated_source_observed'
    } elseif ($MountText -match '(?m)^bind\|') {
        'other_bind_source_observed'
    } else {
        'no_bind_mount_observed'
    }
    return [ordered]@{
        classification = $classification
        mounts = $MountText
    }
}

function Get-DataCapacityDiagnostics {
    param($DockerDataDf, $DiskUsage)

    $AvailableBytes = $null
    if ($null -ne $DockerDataDf -and $DockerDataDf.returncode -eq 0) {
        $DfLines = @($DockerDataDf.output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($DfLines.Count -gt 1) {
            $Fields = @($DfLines[-1] -split '\s+' | Where-Object { $_ })
            if ($Fields.Count -ge 4 -and $Fields[3] -match '^\d+$') {
                $AvailableBytes = [int64]$Fields[3]
            }
        }
    }
    $MinimumReserveBytes = [int64](4 * 1024 * 1024 * 1024)
    $classification = if ($null -ne $AvailableBytes -and $AvailableBytes -ge $MinimumReserveBytes) {
        'reserve_at_least_4_gib'
    } elseif ($null -ne $AvailableBytes) {
        'reserve_below_4_gib'
    } elseif ($DiskUsage.returncode -eq 0) {
        'usage_observed_reserve_unverified'
    } else {
        'unavailable'
    }
    return [ordered]@{
        classification = $classification
        available_bytes = $AvailableBytes
        minimum_reserve_bytes = $MinimumReserveBytes
        docker_data_df = if ($null -eq $DockerDataDf) { 'wsl_query_unavailable' } else { $DockerDataDf.output }
        docker_system_df = $DiskUsage.output
    }
}

function Collect-Diagnostics {
    # Diagnostics are evidence collection, not the recovery wait. Always honor
    # CommandTimeoutSeconds per probe even when the global TimeoutSeconds budget
    # is already low; otherwise mid-suite probes starve and restart/start look
    # "unavailable" or readiness never sees a successful action.
    $DesktopBundle = Get-DesktopDiagnosticBundle
    $Diagnostics.desktop = $DesktopBundle.Desktop
    $DesktopRows = $DesktopBundle.Rows

    $Probes = Get-DockerProbeBundle
    $LocalEngine = Get-LocalEngineProbe

    $Diagnostics.daemon_identity = [ordered]@{
        classification = if ($Probes.Version.returncode -eq 0 -and $Probes.Info.returncode -eq 0) { 'observed' } else { 'unavailable' }
        active_context = ($Probes.ContextShow.output.Trim())
        version = $Probes.Version.output
        info = $Probes.Info.output
    }
    $Diagnostics.engine_topology = Get-EngineTopologyDiagnostics `
        -DesktopRows $DesktopRows `
        -Version $Probes.Version `
        -Info $Probes.Info `
        -LocalEngine $LocalEngine `
        -ContextList $Probes.ContextList

    $WslBundle = Get-WslDiagnosticBundle
    $Diagnostics.wsl_integration = $WslBundle.Integration
    $Diagnostics.vhd_attachment = Get-VhdAttachmentDiagnostics `
        -DesktopRows $DesktopRows `
        -WslStatus $WslBundle.Status `
        -WslList $WslBundle.List
    $Diagnostics.project_origins = Get-ProjectOriginDiagnostics -Compose $Probes.Compose
    $Diagnostics.port_owners = Get-PortOwnerDiagnostics -Containers $Probes.Containers
    $Diagnostics.bind_path_translation = Get-BindPathDiagnostics -Mounts $Probes.Mounts
    $Diagnostics.data_capacity = Get-DataCapacityDiagnostics `
        -DockerDataDf $WslBundle.DockerDataDf `
        -DiskUsage $Probes.DiskUsage
}

function Write-RecoveryReport {
    param([string]$Cause, [bool]$Ok, [string[]]$RecordedActions)

    $Target = [System.IO.Path]::GetFullPath($ReportPath)
    $Parent = [System.IO.Path]::GetDirectoryName($Target)
    if (-not [string]::IsNullOrWhiteSpace($Parent)) {
        [System.IO.Directory]::CreateDirectory($Parent) | Out-Null
    }
    $Payload = [ordered]@{
        schema_version = 'bioetl-docker-desktop-recovery-v2'
        generated_at = (Get-Date).ToUniversalTime().ToString('o')
        ok = $Ok
        primary_cause = $Cause
        actions = $RecordedActions
        elapsed_seconds = [math]::Round(((Get-Date) - $Started).TotalSeconds, 3)
        command_timeout_seconds = $CommandTimeoutSeconds
        diagnostics = $Diagnostics
        observations = $Observations
        redaction_applied = $true
        last_resort_requested = [bool]$ConfirmLastResort
        last_resort_token_valid = ($LastResortConfirmation -ceq $LastResortToken)
    }
    $Temporary = "$Target.tmp"
    # Evidence capture must always land on disk, even when the operator passed
    # -WhatIf for last-resort ShouldProcess confirmation. Cmdlet -WhatIf:$false is
    # unreliable under SupportsShouldProcess; use BCL IO which ignores WhatIf.
    $Json = (Protect-SensitiveValue $Payload) | ConvertTo-Json -Depth 12
    $Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Temporary, ($Json + [Environment]::NewLine), $Utf8NoBom)
    if ([System.IO.File]::Exists($Target)) {
        [System.IO.File]::Delete($Target)
    }
    [System.IO.File]::Move($Temporary, $Target)
}

$InitiallyReady = Test-DockerReady
Collect-Diagnostics
if ($InitiallyReady) {
    Write-RecoveryReport 'none' $true @('already_ready')
    Write-Output 'Docker daemon is already ready; bounded diagnostics were captured'
    exit 0
}

$RestartSupported = [bool]$Diagnostics.desktop.capabilities.restart
$StopSupported = [bool]$Diagnostics.desktop.capabilities.stop
$StartSupported = [bool]$Diagnostics.desktop.capabilities.start
if ($RestartSupported) {
    $Restart = Invoke-BoundedCommand 'docker' @('desktop', 'restart', '--detach') -AllowOverrun
    $Actions.Add('docker_desktop_restart')
    if (($Restart.returncode -ne 0) -or $Restart.timed_out) {
        if (-not ($StopSupported -and $StartSupported)) {
            Write-RecoveryReport 'desktop_restart_failed' $false $Actions
            throw 'Supported Docker Desktop restart failed and the supported stop/start fallback is unavailable.'
        }
        $Actions.Add('docker_desktop_restart_failed_bounded')
        $Stop = Invoke-BoundedCommand 'docker' @('desktop', 'stop', '--detach') -AllowOverrun
        $Actions.Add('docker_desktop_stop')
        if (($Stop.returncode -ne 0) -or $Stop.timed_out) {
            Write-RecoveryReport 'desktop_stop_failed' $false $Actions
            throw 'Supported Docker Desktop stop fallback did not complete successfully within its command deadline.'
        }
        $Start = Invoke-BoundedCommand 'docker' @('desktop', 'start', '--detach') -AllowOverrun
        $Actions.Add('docker_desktop_start')
        if (($Start.returncode -ne 0) -or $Start.timed_out) {
            Write-RecoveryReport 'desktop_start_failed' $false $Actions
            throw 'Supported Docker Desktop start fallback did not complete successfully within its command deadline.'
        }
    }
} elseif ($StartSupported) {
    $Start = Invoke-BoundedCommand 'docker' @('desktop', 'start', '--detach') -AllowOverrun
    $Actions.Add('docker_desktop_start')
    if (($Start.returncode -ne 0) -or $Start.timed_out) {
        Write-RecoveryReport 'desktop_start_failed' $false $Actions
        throw 'Supported Docker Desktop start did not complete successfully within its command deadline.'
    }
} else {
    Write-RecoveryReport 'desktop_cli_unavailable' $false $Actions
    throw 'Docker Desktop CLI restart/start is unavailable; no unbounded launcher was invoked.'
}

# Always attempt at least one readiness probe after a supported recovery action,
# even when diagnostics consumed the global wait budget. The action itself is
# bounded; a zero remaining budget must not hide a successful restart.
if (Test-DockerReady -AllowOverrun) {
    Write-RecoveryReport 'none' $true $Actions
    Write-Output 'Docker daemon recovered within the bounded deadline'
    exit 0
}

while ((Get-RemainingMilliseconds) -gt 0) {
    if (Test-DockerReady) {
        Write-RecoveryReport 'none' $true $Actions
        Write-Output 'Docker daemon recovered within the bounded deadline'
        exit 0
    }
    $SleepMilliseconds = [math]::Min(2000, (Get-RemainingMilliseconds))
    if ($SleepMilliseconds -gt 0) { Start-Sleep -Milliseconds $SleepMilliseconds }
}

$Actions.Add('bounded_recovery_exhausted')
if ($ConfirmLastResort) {
    $Actions.Add('last_resort_requested')
    $ConfirmExplicitlyDisabled = (
        $PSBoundParameters.ContainsKey('Confirm') -and
        -not [bool]$PSBoundParameters['Confirm']
    )
    if ($LastResortConfirmation -cne $LastResortToken) {
        $Actions.Add('last_resort_token_rejected')
    } elseif ($ConfirmExplicitlyDisabled) {
        $Actions.Add('last_resort_confirmation_bypass_rejected')
    } else {
        $Desktop = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
        if ($Desktop) {
            if ($PSCmdlet.ShouldProcess('Docker Desktop', 'force terminate after evidence capture as the explicitly confirmed last resort')) {
                Write-RecoveryReport 'confirmed_last_resort_requested' $false $Actions
                $Desktop | Stop-Process -Force
                throw 'Confirmed last-resort termination completed; review the report before rerunning bounded recovery.'
            }
            $Actions.Add('last_resort_not_confirmed')
        } else {
            $Actions.Add('last_resort_process_not_found')
        }
    }
}

Write-RecoveryReport 'desktop_recovery_timeout' $false $Actions
throw "Docker Desktop did not recover within $TimeoutSeconds seconds; no destructive fallback was performed."
