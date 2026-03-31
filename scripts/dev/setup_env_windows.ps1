Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../..")
Set-Location $RepoRoot

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $env:TEMP "uv-cache"
}

if (-not $env:UV_LINK_MODE) {
    $env:UV_LINK_MODE = "copy"
}

if (-not $env:UV_HTTP_TIMEOUT) {
    $env:UV_HTTP_TIMEOUT = "180"
}

$VenvDir = Join-Path $RepoRoot ".venv-win"
$VenvPython = Join-Path $VenvDir "Scripts/python.exe"

if ((Test-Path (Join-Path $RepoRoot ".venv")) -and -not (Test-Path (Join-Path $RepoRoot ".venv/Scripts/python.exe"))) {
    Write-Host "[setup_env_windows][hint] Found a non-Windows .venv. It will be ignored in favor of .venv-win."
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv venv $VenvDir --python 3.13
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[setup_env_windows][error] uv venv failed."
        exit $LASTEXITCODE
    }

    $env:VIRTUAL_ENV = $VenvDir
    $env:PATH = "$VenvDir\Scripts;$env:PATH"
    uv sync --active --extra dev --extra tracing
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[setup_env_windows][error] uv sync failed."
        Write-Host "[setup_env_windows][hint] Retry with the same command; UV_HTTP_TIMEOUT defaults to $env:UV_HTTP_TIMEOUT seconds."
        exit $LASTEXITCODE
    }
} else {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.13 -m venv $VenvDir
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m venv $VenvDir
    } else {
        Write-Error "[setup_env_windows][error] Neither uv, py, nor python is available."
        exit 1
    }

    & $VenvPython -m pip install --upgrade pip setuptools wheel
    & $VenvPython -m pip install -e ".[dev,tracing]"
}

Write-Host "[setup_env_windows][ok] Environment ready at .venv-win"
Write-Host "[setup_env_windows][hint] Activate with: .\.venv-win\Scripts\Activate.ps1"
Write-Host "[setup_env_windows][hint] Run tests with: .\scripts\dev\run_pytest.ps1 tests\ --timeout=120 -n 4 --lf"
