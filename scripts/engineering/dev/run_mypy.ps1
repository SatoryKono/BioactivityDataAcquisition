Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
Set-Location $RepoRoot

$ArgsList = @()
$MypyNarrow = $false
foreach ($Arg in $args) {
    if ($Arg -eq "--narrow") {
        $MypyNarrow = $true
        continue
    }
    $ArgsList += $Arg
}

if ($ArgsList.Count -eq 0) {
    $ArgsList = @("--config-file", "pyproject.toml", "--strict", "src/bioetl")
}

if ($MypyNarrow) {
    $ArgsList = @("--follow-imports=skip") + $ArgsList
}

$HasCacheDir = $false
foreach ($Arg in $ArgsList) {
    if ($Arg -eq "--cache-dir") {
        $HasCacheDir = $true
        break
    }
}

if (-not $HasCacheDir) {
    $DefaultMypyCacheDir = if ($env:BIOETL_MYPY_CACHE_DIR) {
        $env:BIOETL_MYPY_CACHE_DIR
    } else {
        ".mypy_cache/windows"
    }
    $ArgsList = @("--cache-dir", $DefaultMypyCacheDir) + $ArgsList
}

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $env:TEMP "uv-cache"
}

if (-not $env:UV_LINK_MODE) {
    $env:UV_LINK_MODE = "copy"
}

$WindowsVenvPython = Join-Path $RepoRoot ".venv-win/Scripts/python.exe"
if (Test-Path $WindowsVenvPython) {
    & $WindowsVenvPython -m mypy @ArgsList
    exit $LASTEXITCODE
}

$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m mypy @ArgsList
    exit $LASTEXITCODE
}

if ((Test-Path (Join-Path $RepoRoot ".venv")) -or (Test-Path (Join-Path $RepoRoot ".venv-wsl"))) {
    Write-Host "[run_mypy][hint] A WSL/Linux virtualenv was detected. PowerShell should use .venv-win."
    Write-Host "[run_mypy][hint] Bootstrap it with: .\scripts\engineering\dev\setup_env_windows.ps1"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python -m mypy @ArgsList
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m mypy @ArgsList
    exit $LASTEXITCODE
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 -m mypy @ArgsList
    exit $LASTEXITCODE
}

Write-Error "[run_mypy][error] Python runtime is not available."
Write-Host "[run_mypy][hint] Install dependencies first:"
Write-Host "  .\scripts\engineering\dev\setup_env_windows.ps1"
exit 1
