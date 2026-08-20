#requires -Version 5.1
<#
.SYNOPSIS
    Configures the BioETL project in WSL from Windows PowerShell.

.DESCRIPTION
    - Resolves and translates a Windows repository path with wslpath.
    - Passes native command arguments directly to wsl.exe, without routing
      user-controlled paths through `bash -lc`.
    - Installs the baseline WSL packages unless -SkipSystemPackages is used.
    - Installs uv for the normal WSL user when it is missing.
    - Delegates Python environment creation to the canonical
      scripts/engineering/dev/setup_env_wsl.sh script.

.EXAMPLE
    .\setup_bioetl_wsl.ps1 `
        -Distro "Ubuntu" `
        -ProjectPath "E:\github\BioactivityDataAcquisition"

.EXAMPLE
    .\setup_bioetl_wsl.ps1 `
        -Distro "Ubuntu" `
        -WslProjectPath "/home/fedor/src/BioactivityDataAcquisition" `
        -RecreateVenv
#>

[CmdletBinding(DefaultParameterSetName = 'WindowsPath')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'WindowsPath')]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectPath,

    [Parameter(Mandatory = $true, ParameterSetName = 'WslPath')]
    [ValidateNotNullOrEmpty()]
    [string]$WslProjectPath,

    [ValidateNotNullOrEmpty()]
    [string]$Distro = 'Ubuntu',

    [ValidateNotNullOrEmpty()]
    [string]$VenvPath = '~/.venvs/bioetl',

    [switch]$RecreateVenv,
    [switch]$SkipSystemPackages,
    [switch]$IncludeDocs,
    [switch]$IncludeFullTests,
    [switch]$IncludeExport,
    [switch]$IncludeMcp,
    [switch]$InstallPreCommitHooks,
    [switch]$SkipSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Show-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[setup_bioetl_wsl] $Message"
}

function Convert-NativeOutputToText {
    param([object[]]$Output)

    $lines = foreach ($item in $Output) {
        if ($null -eq $item) {
            continue
        }
        ([string]$item).Replace([char]0, '')
    }
    return (($lines -join [Environment]::NewLine).Trim())
}

function Invoke-WslCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string[]]$ArgumentList,

        [string]$User
    )

    $wslArguments = @('--distribution', $Distro)
    if (-not [string]::IsNullOrWhiteSpace($User)) {
        $wslArguments += @('--user', $User)
    }
    $wslArguments += '--exec'
    $wslArguments += $ArgumentList

    # Windows PowerShell 5.1 converts native stderr records into
    # NativeCommandError when ErrorActionPreference is Stop. Capture the
    # complete native output first, then make the exit code authoritative.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $nativeOutput = @(& wsl.exe @wslArguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $text = Convert-NativeOutputToText -Output $nativeOutput
    if ($exitCode -ne 0) {
        $commandText = 'wsl.exe ' + ($wslArguments -join ' ')
        if ([string]::IsNullOrWhiteSpace($text)) {
            $text = '<no output>'
        }
        throw "WSL command failed with exit code ${exitCode}: ${commandText}`n${text}"
    }

    return $text
}

function Resolve-WindowsProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    $providerPath = $resolved.ProviderPath
    if ([string]::IsNullOrWhiteSpace($providerPath)) {
        throw "Could not resolve Windows project path: $Path"
    }
    return $providerPath.TrimEnd('\')
}

function Convert-WindowsPathToWslPath {
    param([Parameter(Mandatory = $true)][string]$WindowsPath)

    # Critical detail: do not use bash -lc here. Passing the path as one native
    # argument prevents Bash from consuming Windows backslashes as escapes.
    $translated = Invoke-WslCommand -ArgumentList @(
        'wslpath',
        '-a',
        '-u',
        $WindowsPath
    )

    $candidate = ($translated -split "`r?`n" | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_)
    } | Select-Object -Last 1).Trim()

    if (-not $candidate.StartsWith('/')) {
        throw "wslpath returned an invalid WSL path: $translated"
    }
    return $candidate.TrimEnd('/')
}

function Resolve-WslVenvPath {
    param(
        [Parameter(Mandatory = $true)][string]$ConfiguredPath,
        [Parameter(Mandatory = $true)][string]$HomePath
    )

    if ($ConfiguredPath -eq '~') {
        return $HomePath
    }
    if ($ConfiguredPath.StartsWith('~/')) {
        return $HomePath.TrimEnd('/') + '/' + $ConfiguredPath.Substring(2)
    }
    if (-not $ConfiguredPath.StartsWith('/')) {
        throw "VenvPath must be absolute or start with '~/' in WSL: $ConfiguredPath"
    }
    return $ConfiguredPath.TrimEnd('/')
}

function Assert-SafeVenvRemoval {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate,
        [Parameter(Mandatory = $true)][string]$HomePath,
        [Parameter(Mandatory = $true)][string]$RepositoryPath
    )

    $normalized = $Candidate.TrimEnd('/')
    $forbidden = @(
        '',
        '/',
        '/home',
        '/mnt',
        $HomePath.TrimEnd('/'),
        $RepositoryPath.TrimEnd('/')
    )

    if ($forbidden -contains $normalized) {
        throw "Refusing to remove unsafe virtual-environment path: $Candidate"
    }
    if ($RepositoryPath.StartsWith($normalized + '/', [System.StringComparison]::Ordinal)) {
        throw "Refusing to remove a parent directory of the repository: $Candidate"
    }
}

function Test-WslCommandAvailable {
    param([Parameter(Mandatory = $true)][string]$CommandName)

    $result = Invoke-WslCommand -ArgumentList @(
        'sh',
        '-lc',
        'command -v "$1" >/dev/null 2>&1; printf "%s" "$?"',
        'bioetl-command-check',
        $CommandName
    )
    return $result.Trim() -eq '0'
}

if ($null -eq (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'wsl.exe was not found. Install or enable WSL 2 first.'
}

Show-Step 'Checking WSL availability'
$kernel = Invoke-WslCommand -ArgumentList @('uname', '-sr')
Write-Host "WSL ready: $kernel"

if ($PSCmdlet.ParameterSetName -eq 'WindowsPath') {
    Show-Step 'Translating repository path for WSL'
    $resolvedWindowsProjectPath = Resolve-WindowsProjectPath -Path $ProjectPath
    $WslProjectPath = Convert-WindowsPathToWslPath -WindowsPath $resolvedWindowsProjectPath
}
else {
    $WslProjectPath = $WslProjectPath.TrimEnd('/')
}

Write-Host "[setup_bioetl_wsl] Repository: $WslProjectPath"

foreach ($requiredFile in @(
    'pyproject.toml',
    'uv.lock',
    'scripts/engineering/dev/setup_env_wsl.sh'
)) {
    $null = Invoke-WslCommand -ArgumentList @(
        'test',
        '-f',
        "$WslProjectPath/$requiredFile"
    )
}

$wslHome = Invoke-WslCommand -ArgumentList @(
    'sh',
    '-lc',
    'printf "%s" "$HOME"'
)
$wslHome = $wslHome.Trim()
if (-not $wslHome.StartsWith('/')) {
    throw "Could not determine WSL home directory: $wslHome"
}
$resolvedVenvPath = Resolve-WslVenvPath -ConfiguredPath $VenvPath -HomePath $wslHome
$venvPython = "$resolvedVenvPath/bin/python"

if (-not $SkipSystemPackages) {
    Show-Step 'Installing baseline WSL packages'
    $null = Invoke-WslCommand -User 'root' -ArgumentList @(
        'env',
        'DEBIAN_FRONTEND=noninteractive',
        'apt-get',
        'update'
    )
    $null = Invoke-WslCommand -User 'root' -ArgumentList @(
        'env',
        'DEBIAN_FRONTEND=noninteractive',
        'apt-get',
        'install',
        '-y',
        'git',
        'git-lfs',
        'curl',
        'ca-certificates',
        'make',
        'python3',
        'python3-venv',
        'python3-pip',
        'jq',
        'unzip',
        'zip',
        'rsync',
        'ripgrep',
        'fd-find',
        'tree',
        'less',
        'lsof',
        'procps',
        'shellcheck',
        'zstd'
    )
}

Show-Step 'Configuring Git LFS'
$null = Invoke-WslCommand -ArgumentList @('git', 'lfs', 'install')

$uvPath = Invoke-WslCommand -ArgumentList @(
    'sh',
    '-lc',
    'PATH="$HOME/.local/bin:$PATH"; command -v uv || true'
)
$uvPath = $uvPath.Trim()
if ([string]::IsNullOrWhiteSpace($uvPath)) {
    Show-Step 'Installing uv for the WSL user'
    $null = Invoke-WslCommand -ArgumentList @(
        'bash',
        '-lc',
        'curl -LsSf https://astral.sh/uv/install.sh | sh'
    )
    $uvPath = Invoke-WslCommand -ArgumentList @(
        'sh',
        '-lc',
        'PATH="$HOME/.local/bin:$PATH"; command -v uv'
    )
    $uvPath = $uvPath.Trim()
}

if ($RecreateVenv) {
    Assert-SafeVenvRemoval `
        -Candidate $resolvedVenvPath `
        -HomePath $wslHome `
        -RepositoryPath $WslProjectPath
    Show-Step "Removing existing WSL venv: $resolvedVenvPath"
    $null = Invoke-WslCommand -ArgumentList @(
        'rm',
        '-rf',
        '--',
        $resolvedVenvPath
    )
}

Show-Step 'Running the canonical BioETL WSL bootstrap'
$runtimePath = "$wslHome/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
$null = Invoke-WslCommand -ArgumentList @(
    'env',
    "BIOETL_WSL_VENV_DIR=$resolvedVenvPath",
    "PATH=$runtimePath",
    'bash',
    "$WslProjectPath/scripts/engineering/dev/setup_env_wsl.sh"
)

$extraNames = @('dev', 'tracing')
if ($IncludeDocs) {
    $extraNames += 'docs'
}
if ($IncludeFullTests) {
    $extraNames += @('tests', 'tests_full')
}
if ($IncludeExport) {
    $extraNames += 'export'
}

if ($IncludeDocs -or $IncludeFullTests -or $IncludeExport) {
    Show-Step 'Synchronizing requested optional Python extras'
    $syncArguments = @(
        'env',
        "VIRTUAL_ENV=$resolvedVenvPath",
        'UV_CACHE_DIR=/tmp/uv-cache',
        'UV_LINK_MODE=copy',
        'UV_HTTP_TIMEOUT=180',
        'UV_NO_BUILD=1',
        $uvPath,
        '--project',
        $WslProjectPath,
        'sync',
        '--active',
        '--frozen',
        '--no-build'
    )
    foreach ($extraName in ($extraNames | Select-Object -Unique)) {
        $syncArguments += @('--extra', $extraName)
    }
    $null = Invoke-WslCommand -ArgumentList $syncArguments
}

if ($InstallPreCommitHooks) {
    Show-Step 'Installing pre-commit hooks'
    $null = Invoke-WslCommand -ArgumentList @(
        'sh',
        '-c',
        'cd "$1" && exec "$2" -m pre_commit install',
        'bioetl-pre-commit',
        $WslProjectPath,
        $venvPython
    )
}

if ($IncludeMcp) {
    Show-Step 'Installing Node/MCP dependencies from package-lock.json'
    if (-not (Test-WslCommandAvailable -CommandName 'npm')) {
        throw 'npm is required for -IncludeMcp. Install a supported Node.js version in WSL first.'
    }
    $null = Invoke-WslCommand -ArgumentList @(
        'sh',
        '-c',
        'cd "$1" && exec npm ci',
        'bioetl-npm-ci',
        $WslProjectPath
    )
}

if (-not $SkipSmoke) {
    Show-Step 'Running smoke checks'
    $pythonVersion = Invoke-WslCommand -ArgumentList @($venvPython, '--version')
    Write-Host "[setup_bioetl_wsl] $pythonVersion"
    $smoke = Invoke-WslCommand -ArgumentList @(
        'env',
        "PYTHONPATH=$WslProjectPath/src",
        $venvPython,
        '-c',
        'import sys, bioetl; print(sys.executable); print("bioetl import: OK")'
    )
    Write-Host $smoke
}

Write-Host ''
Write-Host '[setup_bioetl_wsl] Setup completed successfully.'
Write-Host "[setup_bioetl_wsl] WSL repository: $WslProjectPath"
Write-Host "[setup_bioetl_wsl] WSL venv:       $resolvedVenvPath"
Write-Host "[setup_bioetl_wsl] Activate with:  source '$resolvedVenvPath/bin/activate'"
