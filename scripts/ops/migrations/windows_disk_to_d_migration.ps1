#requires -Version 5.1
<#
.SYNOPSIS
  Executes a controlled, low-risk C:→D: migration plan for Windows user applications.

.DESCRIPTION
  This script materializes the candidate list from
  D:\migration-plan-C-to-D.md, groups items by wave, and emits executable but
  non-destructive commands (backup + validation checklist) for each application.

  It intentionally does not run uninstall/install operations directly, because
  Windows installer UX and licensing behavior differ by version.

  Use this as a strict checklist runner:
  - validate preconditions
  - prepare backups/logs
  - execute each approved command group manually
#>

[CmdletBinding()]
param(
    [string]$PlanPath = 'D:\migration-plan-C-to-D.md',
    [string]$BackupRoot = 'D:\Migration_Backup\2026-07-21',
    [string]$LogRoot = 'D:\Migration_Logs',
    [int]$MinFreeDGB = 85,
    [ValidateSet('Wave0', 'Wave1', 'Wave2', 'Wave3', 'Wave4')]
    [string[]]$Waves = @('Wave1', 'Wave2', 'Wave3'),
    [string[]]$OnlyApps = @(),
    [switch]$ListOnly,
    [switch]$Check,
    [switch]$FailOnUnresolved
)

$ErrorActionPreference = 'Stop'

$WaveMap = [ordered]@{
    Wave0 = @()
    Wave1 = @('APP-15','APP-16','APP-17','APP-18','APP-19','APP-11','APP-12','APP-13','APP-14','APP-06','APP-07','APP-08','APP-09','APP-10','APP-01','APP-02','APP-03','APP-04','APP-05')
    Wave2 = @('DEV-01','DEV-02','DEV-03','DEV-04','DEV-05','DEV-06','DEV-07','DEV-08','DEV-09','DEV-10','DEV-11','DEV-12','DEV-13','DEV-14','DEV-15','DEV-16','DEV-17','DEV-18','DEV-19','DEV-20','DEV-21','DEV-22','DEV-23')
    Wave3 = @('SCI-01','SCI-02','SCI-03','SCI-04','SCI-05','SCI-06','SCI-07','SCI-08','SCI-09','SCI-10')
    Wave4 = @('Store')
}

$CatalogOverrides = [ordered]@{
    'APP-01' = @{ Source = 'C:\Users\Fedor\AppData\Local\Programs\Opera\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Opera Software\'; Target = 'D:\Users\Fedor\AppData\Local\Programs\Opera\'; DataTarget = 'D:\AppData\Opera\Profile\'; InstallHint = 'Reinstall from official installer'; },
    'APP-02' = @{ Source = 'C:\Users\Fedor\AppData\Local\Programs\eXpress\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\eXpress\'; Target = 'D:\Users\Fedor\AppData\Local\Programs\eXpress\'; DataTarget = 'D:\Migration_Backup\2026-07-21\eXpress\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-03' = @{ Source = 'C:\Users\Fedor\AppData\Local\Programs\Antigravity\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Antigravity\'; Target = 'D:\Users\Fedor\AppData\Local\Programs\Antigravity\'; DataTarget = 'D:\Migration_Backup\2026-07-21\Antigravity\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-04' = @{ Source = 'C:\Users\Fedor\AppData\Local\Programs\Microsoft VS Code\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Code\'; Target = 'D:\Users\Fedor\AppData\Local\Programs\Microsoft VS Code\'; DataTarget = 'D:\Migration_Backup\2026-07-21\Code\Data\'; InstallHint = 'Reinstall on D:, then migrate extensions manifest manually' },
    'APP-05' = @{ Source = 'C:\Users\Fedor\AppData\Roaming\Zoom\'; Target = 'D:\Program Files\Zoom\'; DataTarget = 'D:\Migration_Backup\2026-07-21\Zoom\Data\'; DataSource = $null; InstallHint = 'Installer must support custom location' },
    'APP-06' = @{ Source = 'C:\Program Files\LibreOffice\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\LibreOffice\'; Target = 'D:\Program Files\LibreOffice\'; DataTarget = 'D:\Migration_Backup\2026-07-21\LibreOffice\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-07' = @{ Source = 'C:\Program Files\Inkscape\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Inkscape\'; Target = 'D:\Program Files\Inkscape\'; DataTarget = 'D:\Migration_Backup\2026-07-21\Inkscape\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-08' = @{ Source = 'C:\Program Files\Koala Clash\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Koala-Clash\'; Target = 'D:\Program Files\Koala Clash\'; DataTarget = 'D:\Migration_Backup\2026-07-21\KoalaClash\Data\'; InstallHint = 'Reinstall on D: (postpone if recent)' },
    'APP-09' = @{ Source = 'C:\Program Files\obs-studio\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\obs-studio\'; Target = 'D:\Program Files\obs-studio\'; DataTarget = 'D:\Migration_Backup\2026-07-21\obs-studio\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-10' = @{ Source = 'C:\Program Files (x86)\Zotero\'; DataSource = 'C:\Users\Fedor\Zotero\'; DataTarget = 'D:\AppData\Zotero\Data\'; Target = 'D:\Program Files\Zotero\'; InstallHint = 'Reinstall on D: and repoint data directory' },
    'APP-11' = @{ Source = 'C:\Program Files (x86)\Data Match Enterprise\'; DataSource = 'C:\ProgramData\DataMatch Enterprise 3\'; Target = 'D:\Program Files (x86)\Data Match Enterprise\'; DataTarget = 'D:\Migration_Backup\2026-07-21\DataMatch\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-12' = @{ Source = 'C:\Program Files (x86)\ACDFREE11\'; DataSource = 'C:\ProgramData\Advanced Chemistry Development\'; Target = 'D:\Program Files (x86)\ACDFREE11\'; DataTarget = 'D:\Migration_Backup\2026-07-21\ACDFREE11\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-13' = @{ Source = 'C:\Program Files (x86)\PDF Enhancer\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Apago\'; Target = 'D:\Program Files (x86)\PDF Enhancer\'; DataTarget = 'D:\Migration_Backup\2026-07-21\ApagoPDFEnhancer\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-14' = @{ Source = 'C:\Program Files (x86)\Apago\PDF Shrink\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Apago\PDF Shrink\'; Target = 'D:\Program Files (x86)\Apago\PDF Shrink\'; DataTarget = 'D:\Migration_Backup\2026-07-21\ApagoPDFShrink\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-15' = @{ Source = 'C:\Program Files\VS Revo Group\Revo Uninstaller\'; Target = 'D:\Program Files\VS Revo Group\Revo Uninstaller\'; DataSource = $null; DataTarget = 'D:\Migration_Backup\2026-07-21\RevoUninstaller\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-16' = @{ Source = 'C:\Program Files (x86)\XnView\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\XnView\'; Target = 'D:\Program Files (x86)\XnView\'; DataTarget = 'D:\Migration_Backup\2026-07-21\XnView\Data\'; InstallHint = 'Reinstall on D:' },
    'APP-17' = @{ Source = 'C:\Program Files (x86)\Sizer\'; Target = 'D:\Program Files (x86)\Sizer\'; DataSource = $null; DataTarget = $null; InstallHint = 'Move together with wave' },
    'APP-18' = @{ Source = 'C:\Program Files\Unlocker\'; Target = 'D:\Program Files\Unlocker\'; DataSource = $null; DataTarget = $null; InstallHint = 'Reinstall on D:' },
    'APP-19' = @{ Source = 'C:\Program Files (x86)\University of Illinois\VMD\'; DataSource = $null; Target = 'D:\Program Files (x86)\University of Illinois\VMD\'; DataTarget = $null; InstallHint = 'Reinstall on D:' },
    'DEV-01' = @{ Source = 'C:\Program Files\JetBrains\IntelliJ IDEA 2025.3\'; Target = 'D:\Program Files\JetBrains\IntelliJ IDEA 2025.3\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\JetBrains\IntelliJIdea2025.3\'; DataTarget='D:\Migration_Backup\2026-07-21\IntelliJ\Data\'; InstallHint='JetBrains Toolbox or installer with custom path' },
    'DEV-02' = @{ Source = 'C:\Program Files\JetBrains\DataGrip 2025.3.5\'; Target = 'D:\Program Files\JetBrains\DataGrip 2025.3.5\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\JetBrains\Datagrip\'; DataTarget='D:\Migration_Backup\2026-07-21\DataGrip\Data\'; InstallHint='JetBrains Toolbox or installer with custom path' },
    'DEV-03' = @{ Source = 'C:\Windows\System32'; Target = $null; InstallHint = 'CLI check first: where.exe and path references in build scripts' },
    'DEV-16' = @{ Source = 'C:\Program Files\Python39\'; Target = 'D:\Runtimes\Python39\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\Python\Python39\'; DataTarget='D:\Migration_Backup\2026-07-21\Python39\Data\'; InstallHint='Manual reinstall + env refresh' },
    'DEV-17' = @{ Source = 'Microsoft Store Python 3.9'; Target = 'Windows Settings -> Move'; DataSource = $null; DataTarget = $null; InstallHint='Use Move app button if available' },
    'DEV-18' = @{ Source = 'C:\Program Files\OpenBabel\'; Target = 'D:\Program Files\OpenBabel\'; DataSource = $null; InstallHint='Keep / validate D:\_programs\OpenBabel-3.1.1 first' },
    'DEV-19' = @{ Source = 'C:\Program Files\OpenBabel2\'; Target = 'D:\Program Files\OpenBabel2\'; DataSource = $null; InstallHint='Remove or reinstall on D: after dependency check' },
    'DEV-20' = @{ Source = 'C:\Program Files\OpenBabel2\'; Target = 'D:\Program Files\OpenBabel2\'; DataSource = $null; InstallHint='Remove or reinstall on D: after dependency check' },
    'DEV-21' = @{ Source = 'C:\Program Files\Pandoc\'; Target = 'D:\Program Files\Pandoc\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\pandoc\'; DataTarget='D:\Migration_Backup\2026-07-21\Pandoc\Data\'; InstallHint='Reinstall on D:' },
    'DEV-22' = @{ Source = 'C:\Program Files\wkhtmltox\'; Target = 'D:\Program Files\wkhtmltopdf\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\wkhtmltopdf\'; DataTarget='D:\Migration_Backup\2026-07-21\wkhtmltopdf\Data\'; InstallHint='Reinstall on D:' },
    'DEV-23' = @{ Source = 'C:\Program Files (x86)\WinSCP\'; Target = 'D:\Program Files (x86)\WinSCP\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\WinSCP\'; DataTarget='D:\Migration_Backup\2026-07-21\WinSCP\Data\'; InstallHint='Export sessions/config, reinstall on D:' },
    'SCI-01' = @{ Source = 'C:\Program Files (x86)\ABBYY FineReader 12\'; Target = 'D:\Program Files (x86)\ABBYY FineReader 12\'; DataSource = 'C:\Users\Fedor\AppData\Roaming\ABBYY\'; DataTarget='D:\AppData\ABBYY\'; InstallHint='Reinstall on D:, preserve license/deactivation evidence' },
    'SCI-02' = @{ Source = 'C:\Users\Fedor\AppData\Local\Programs\chemofficeplus\'; Target = 'D:\Users\Fedor\AppData\Local\Programs\chemofficeplus\'; DataSource = $null; DataTarget='D:\Migration_Backup\2026-07-21\ChemOfficePlus\Data\'; InstallHint='Reinstall on D: custom path' },
    'SCI-03' = @{ Source = 'C:\Program Files\PerkinElmerInformatics\ChemOffice2022\'; Target = 'D:\Program Files\PerkinElmerInformatics\ChemOffice2022\'; DataSource = 'C:\ProgramData\PerkinElmerInformatics\'; DataTarget='D:\Migration_Backup\2026-07-21\ChemOffice2022\Data\'; InstallHint='Move as bundle only after installer/version validation' },
    'SCI-04' = @{ Source = 'C:\Program Files\Carl Zeiss\'; Target = 'D:\Program Files\Carl Zeiss\'; DataSource = 'C:\ProgramData\Carl Zeiss\'; DataTarget='D:\Migration_Backup\2026-07-21\CarlZeiss\Data\'; InstallHint='Installer-only, one-day block per ZEISS bundle' },
    'SCI-05' = @{ Source = 'C:\Program Files\Carl Zeiss\'; Target = 'D:\Program Files\Carl Zeiss\'; DataSource = $null; DataTarget='D:\Migration_Backup\2026-07-21\CarlZeiss\Data\'; InstallHint='Bundle with SCI-04' },
    'SCI-06' = @{ Source = 'C:\Program Files\Carl Zeiss\'; Target = 'D:\Program Files\Carl Zeiss\'; DataSource = $null; DataTarget='D:\Migration_Backup\2026-07-21\CarlZeiss\Data\'; InstallHint='Bundle with SCI-04' },
    'SCI-07' = @{ Source = 'C:\Users\Fedor\Documents\ZeissPy'; Target = 'D:\Users\Fedor\Documents\ZeissPy'; DataSource = $null; DataTarget='D:\Migration_Backup\2026-07-21\ZeissPy\Data\'; InstallHint='Bundle with SCI-04' },
    'SCI-08' = @{ Source = 'C:\Program Files (x86)\Carl Zeiss\'; Target = 'D:\Program Files (x86)\Carl Zeiss\'; DataSource = 'C:\ProgramData\Carl Zeiss\'; DataTarget='D:\Migration_Backup\2026-07-21\CarlZeiss\Data\'; InstallHint='Bundle with SCI-04' },
    'SCI-09' = @{ Source = 'C:\ProgramData\Carl Zeiss\'; Target = 'D:\ProgramData\Carl Zeiss\'; DataSource = $null; DataTarget='D:\Migration_Backup\2026-07-21\CarlZeiss\License\'; InstallHint='Bundle with SCI-04, preserve license evidence' },
    'SCI-10' = @{ Source = 'C:\Program Files (x86)\Common Files\Carl Zeiss\'; Target = 'D:\Program Files (x86)\Common Files\Carl Zeiss\'; DataSource = $null; DataTarget=$null; InstallHint='Bundle with SCI-04' }
}

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$stamp] $Message"
    Write-Output $line
    if ($script:LogFile) { Add-Content -Path $script:LogFile -Value $line }
}

function Ensure-Directories {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        New-Item -Path $Path -ItemType Directory -Force | Out-Null
    }
}

function Get-FreeSpaceGB {
    param([string]$DriveLetter)
    $drive = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='$DriveLetter'"
    if (-not $drive) { return 0 }
    return [math]::Round($drive.FreeSpace / 1GB, 2)
}

function Parse-PlanCandidates {
    param([string]$PlanFile)
    if (-not (Test-Path -LiteralPath $PlanFile)) {
        throw "Plan file not found: $PlanFile"
    }
    $items = @()
    Get-Content -LiteralPath $PlanFile | ForEach-Object {
        $line = $_
        if ($line -notmatch '^\|\s*(APP|DEV|SCI)-\d+\s*\|') { return }
        if ($line -match '^\|\s*(?<id>APP|DEV|SCI)-(?<num>\d{2})\s*\|\s*(?<app>[^|]+)\s*\|\s*(?<size>[^|]+)\s*\|\s*(?<decision>[^|]+)\s*\|') {
            $id = '{0}-{1}' -f $matches.id, $matches.num
            $items += [pscustomobject]@{
                Id = $id
                Application = $matches.app.Trim()
                Size = $matches.size.Trim()
                Decision = $matches.decision.Trim()
                Source = $null
                DataSource = $null
                Target = $null
                DataTarget = $null
                InstallHint = $null
                Wave = $null
            }
        }
    }
    return $items
}

function Enrich-Candidates {
    param([object[]]$Candidates)
    $waveLookup = @{}
    foreach ($w in $WaveMap.Keys) {
        foreach ($id in $WaveMap[$w]) { $waveLookup[$id] = $w }
    }
    $waveLookup['Store'] = 'Wave4'
    foreach ($item in $Candidates) {
        if ($waveLookup.ContainsKey($item.Id)) {
            $item.Wave = $waveLookup[$item.Id]
        } else {
            $item.Wave = 'Unassigned'
        }
        if ($CatalogOverrides.ContainsKey($item.Id)) {
            $override = $CatalogOverrides[$item.Id]
            foreach ($k in $override.Keys) {
                $item.$k = $override[$k]
            }
        }
    }
    return $Candidates
}

function Get-PlanWave {
    param([object[]]$Candidates,[string[]]$WaveSelection,[string[]]$AppSelection)
    $items = $Candidates | Where-Object { $_.Wave -in $WaveSelection }
    if ($AppSelection -and $AppSelection.Count -gt 0) {
        $items = $items | Where-Object { $_.Id -in $AppSelection }
    }
    return $items
}

function Write-ActionPreview {
    param([object]$Item,[int]$Index)
    Write-Output ('')
    Write-Output ("[{0}] {1} ({2})" -f $Item.Id, $Item.Application, $Item.Size)
    Write-Output ("  Decision:   {0}" -f $Item.Decision)
    if ($Item.Source) { Write-Output ("  Source:     {0}" -f $Item.Source) } else { Write-Output "  Source:     (manual from original plan)" }
    if ($Item.Target) { Write-Output ("  Target:     {0}" -f $Item.Target) } else { Write-Output "  Target:     (manual from original plan)" }
    if ($Item.DataSource) { Write-Output ("  Data src:   {0}" -f $Item.DataSource) }
    if ($Item.DataTarget) { Write-Output ("  Data dst:   {0}" -f $Item.DataTarget) }
    if ($Item.InstallHint) { Write-Output ("  Installer:  {0}" -f $Item.InstallHint) }
    Write-Output "  Commands:"
    if ($Item.Source -and (Test-Path -LiteralPath $Item.Source -ErrorAction SilentlyContinue)) {
        Write-Output ("    robocopy `"{0}`" `"{1}`" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /SL" -f $Item.Source, (Join-Path $BackupRoot $Item.Id))
    } else {
        Write-Output "    # Manual action: review source path before backup"
    }
    Write-Output "    # Validate: installed/uninstall path update, startup entries, CLI path(s), service path, and smoke test"
}

function Emit-WavePlan {
    param([object[]]$Items,[string]$WaveName)
    Write-Output ""
    Write-Output ("=== {0} ===" -f $WaveName)
    if (-not $Items -or $Items.Count -eq 0) {
        Write-Output "No matching entries for this wave."
        return
    }
    $i = 1
    foreach ($item in $Items) {
        Write-ActionPreview -Item $item -Index $i
        $i++
    }
}

function Invoke-SafeChecks {
    if (-not (Test-Path -LiteralPath $BackupRoot)) {
        Ensure-Directories -Path $BackupRoot
    }
    if (-not (Test-Path -LiteralPath $LogRoot)) {
        Ensure-Directories -Path $LogRoot
    }
    $now = Get-Date -Format 'yyyyMMdd_HHmmss'
    $script:LogFile = Join-Path $LogRoot ("migration-{0}.log" -f $now)
    New-Item -Path $script:LogFile -ItemType File -Force | Out-Null

    $freeGb = Get-FreeSpaceGB 'D:'
    Write-Output ("D: free space: {0} GiB" -f $freeGb)
    if ($freeGb -lt $MinFreeDGB) {
        throw "D: has ${freeGb} GiB free, below minimum ${MinFreeDGB} GiB."
    }
}

function Main {
    Invoke-SafeChecks

    $candidates = Parse-PlanCandidates -PlanFile $PlanPath
    $candidates = Enrich-Candidates -Candidates $candidates
    $filtered = Get-PlanWave -Candidates $candidates -WaveSelection $Waves -AppSelection $OnlyApps

    Write-Output "Source plan: $PlanPath"
    Write-Output ("Mode: Check={0} ListOnly={1}" -f $Check.IsPresent, $ListOnly.IsPresent)
    Write-Output ("Found entries: {0}" -f $candidates.Count)
    Write-Output ("Filtered entries: {0}" -f $filtered.Count)

    Write-Log ("Plan read from {0}; filtered entries={1}" -f $PlanPath, $filtered.Count)

    $missingSourceMap = $filtered | Where-Object { [string]::IsNullOrWhiteSpace($_.Source) -or -not (Test-Path -LiteralPath $_.Source -ErrorAction SilentlyContinue) }
    Write-Output ("Entries with unresolved source path: {0}" -f $missingSourceMap.Count)
    foreach ($item in $missingSourceMap) {
        if ([string]::IsNullOrWhiteSpace($item.Source)) {
            Write-Output ("  - {0}: source is unknown in catalog" -f $item.Id)
        } else {
            Write-Output ("  - {0}: path not found now: {1}" -f $item.Id, $item.Source)
        }
    }

    if ($Check) {
        Write-Output "Check completed."
        Write-Output ("Parsed={0}, filtered={1}, unresolved={2}" -f $candidates.Count, $filtered.Count, $missingSourceMap.Count)
        if ($FailOnUnresolved -and $missingSourceMap.Count -gt 0) {
            Write-Output 'Check failed: unresolved sources were found and -FailOnUnresolved was requested.'
            exit 2
        }
        return
    }

    foreach ($wave in $WaveMap.Keys) {
        if ($Waves -notcontains $wave) { continue }
        $items = $filtered | Where-Object { $_.Wave -eq $wave }
        Emit-WavePlan -Items $items -WaveName $wave
    }

    if ($ListOnly) {
        Write-Output ''
        Write-Output 'Dry run completed. No destructive changes were executed.'
        return
    }

    Write-Output ''
    Write-Output 'Execution mode is not supported automatically by design.'
    Write-Output 'Use the printed commands and run installer/manual steps for each app under approved maintenance window.'
}

Main
