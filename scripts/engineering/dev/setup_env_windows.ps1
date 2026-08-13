param(
    [ValidateSet("none", "agentdebugx", "proofagent", "all")]
    [string]$AgentTools = "none"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$ErrorMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Error $ErrorMessage
        exit $LASTEXITCODE
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../../..")
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
    Invoke-CheckedCommand -Command { uv venv $VenvDir --python 3.13 --allow-existing } -ErrorMessage "[setup_env_windows][error] uv venv failed."

    $env:VIRTUAL_ENV = $VenvDir
    $env:PATH = "$VenvDir\Scripts;$env:PATH"
    & uv sync --active --extra dev --extra tests --extra tracing
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[setup_env_windows][error] uv sync failed."
        Write-Host "[setup_env_windows][hint] Retry with the same command; UV_HTTP_TIMEOUT defaults to $env:UV_HTTP_TIMEOUT seconds."
        exit $LASTEXITCODE
    }

    $OptionalExtras = @()
    if ($AgentTools -in @("agentdebugx", "all")) { $OptionalExtras += "agentdebugx" }
    if ($AgentTools -in @("proofagent", "all")) { $OptionalExtras += "proofagent" }
    $InstalledExtras = @()
    $OptionalFailures = 0
    foreach ($Extra in $OptionalExtras) {
        $SyncArgs = @("sync", "--active", "--frozen", "--no-build", "--extra", "dev", "--extra", "tests", "--extra", "tracing")
        foreach ($Installed in $InstalledExtras) { $SyncArgs += @("--extra", $Installed) }
        $SyncArgs += @("--extra", $Extra)
        & uv @SyncArgs
        if ($LASTEXITCODE -eq 0) {
            $InstalledExtras += $Extra
            Write-Host "[setup_env_windows][ok] Optional tool installed: $Extra"
        } else {
            $OptionalFailures = 1
            Write-Error "[setup_env_windows][error] Optional tool failed without blocking the remaining tools: $Extra" -ErrorAction Continue
        }
    }
} else {
    if (-not (Test-Path $VenvPython)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            Invoke-CheckedCommand -Command { py -3.13 -m venv $VenvDir } -ErrorMessage "[setup_env_windows][error] py -3.13 -m venv failed."
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            Invoke-CheckedCommand -Command { python -m venv $VenvDir } -ErrorMessage "[setup_env_windows][error] python -m venv failed."
        } else {
            Write-Error "[setup_env_windows][error] Neither uv, py, nor python is available."
            exit 1
        }

        Invoke-CheckedCommand -Command { & $VenvPython -m ensurepip --upgrade } -ErrorMessage "[setup_env_windows][error] ensurepip failed."
        Invoke-CheckedCommand -Command { & $VenvPython -m pip install --upgrade pip setuptools wheel } -ErrorMessage "[setup_env_windows][error] pip bootstrap failed."
    } else {
        Write-Host "[setup_env_windows][hint] Reusing existing .venv-win; refreshing editable install."
    }

    Invoke-CheckedCommand -Command { & $VenvPython -m pip install -e ".[dev,tests,tracing]" } -ErrorMessage "[setup_env_windows][error] editable install failed."
    $OptionalExtras = @()
    if ($AgentTools -in @("agentdebugx", "all")) { $OptionalExtras += "agentdebugx" }
    if ($AgentTools -in @("proofagent", "all")) { $OptionalExtras += "proofagent" }
    $OptionalFailures = 0
    foreach ($Extra in $OptionalExtras) {
        & $VenvPython -m pip install --only-binary=:all: -e ".[dev,tracing,$Extra]"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[setup_env_windows][ok] Optional tool installed: $Extra"
        } else {
            $OptionalFailures = 1
            Write-Error "[setup_env_windows][error] Optional tool failed without blocking the remaining tools: $Extra" -ErrorAction Continue
        }
    }
}

Write-Host "[setup_env_windows][ok] Environment ready at .venv-win"
Write-Host "[setup_env_windows][hint] Activate with: .\.venv-win\Scripts\Activate.ps1"
Write-Host "[setup_env_windows][hint] Run tests with: .\scripts\engineering\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf"
if ($OptionalFailures -ne 0) {
    exit 1
}
