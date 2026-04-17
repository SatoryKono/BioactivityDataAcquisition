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

if (-not $env:PYTHONPYCACHEPREFIX) {
    $env:PYTHONPYCACHEPREFIX = Join-Path $env:TEMP "bioetl-pycache"
}

$PytestArgs = @($args)
$NeedsDefaultFlags = $true
$PytestNarrow = $false
$CollectOnly = $false
$SkipPreflight = $false
$FilteredArgs = @()

function Test-BenchmarkPluginNeeded {
    param(
        [string[]]$Args
    )

    $PreviousArg = $null
    foreach ($Arg in $Args) {
        if ($Arg -like "tests/benchmarks*" -or $Arg -like "*\tests\benchmarks*") {
            return $true
        }
        if ($Arg -in @("--benchmark-only", "--benchmark-compare")) {
            return $true
        }
        if ($PreviousArg -eq "-m" -and $Arg -like "*benchmark*") {
            return $true
        }
        $PreviousArg = $Arg
    }
    return $false
}

function Test-CoveragePluginNeeded {
    param(
        [string[]]$Args
    )

    foreach ($Arg in $Args) {
        if (
            $Arg -eq "--cov" -or
            $Arg -like "--cov=*" -or
            $Arg -eq "--cov-report" -or
            $Arg -like "--cov-report=*" -or
            $Arg -eq "--cov-config" -or
            $Arg -like "--cov-config=*"
        ) {
            return $true
        }
    }
    return $false
}

function Test-XdistPluginNeeded {
    param(
        [string[]]$Args
    )

    $PreviousArg = $null
    foreach ($Arg in $Args) {
        if (
            $Arg -eq "-n" -or
            $Arg -eq "--numprocesses" -or
            $Arg -like "-n*" -or
            $Arg -eq "--dist" -or
            $Arg -like "--dist=*" -or
            $Arg -eq "--tx" -or
            $Arg -like "--tx=*"
        ) {
            return $true
        }
        if (($PreviousArg -eq "-p" -or $PreviousArg -eq "--plugins") -and $Arg -eq "xdist.plugin") {
            return $true
        }
        $PreviousArg = $Arg
    }
    return $false
}

function Test-PreflightScope {
    param(
        [string[]]$Args
    )

    $SelectedPaths = @()
    foreach ($Arg in $Args) {
        if ($Arg.StartsWith("-")) {
            continue
        }
        $SelectedPaths += $Arg
    }

    if ($SelectedPaths.Count -eq 0) {
        return "full"
    }

    foreach ($PathArg in $SelectedPaths) {
        if (
            $PathArg -eq "tests" -or
            $PathArg -eq "tests/" -or
            $PathArg -eq "tests\" -or
            $PathArg -like "tests/architecture*" -or
            $PathArg -like "tests\architecture*" -or
            $PathArg -like "tests/integration*" -or
            $PathArg -like "tests\integration*" -or
            $PathArg -like "tests/e2e*" -or
            $PathArg -like "tests\e2e*" -or
            $PathArg -like "tests/contract*" -or
            $PathArg -like "tests\contract*" -or
            $PathArg -like "tests/smoke*" -or
            $PathArg -like "tests\smoke*"
        ) {
            return "full"
        }
    }

    return ""
}

foreach ($Arg in $PytestArgs) {
    if ($Arg -eq "--narrow") {
        $PytestNarrow = $true
        continue
    }
    if ($Arg -eq "--skip-preflight") {
        $SkipPreflight = $true
        continue
    }
    if ($Arg -in @("--collect-only", "--co")) {
        $CollectOnly = $true
    }
    if ($Arg -in @("--help", "-h", "--version", "-V")) {
        $NeedsDefaultFlags = $false
    }
    $FilteredArgs += $Arg
}

$PytestArgs = $FilteredArgs
$PreflightScope = ""
if ($env:BIOETL_PREFLIGHT_SCOPE) {
    $PreflightScope = $env:BIOETL_PREFLIGHT_SCOPE
} else {
    $PreflightScope = Test-PreflightScope -Args $PytestArgs
}

if (
    -not $SkipPreflight -and
    $env:BIOETL_SKIP_PREFLIGHT -ne "1" -and
    $env:BIOETL_PREFLIGHT_DONE -ne "1" -and
    $env:BIOETL_PREFLIGHT_ACTIVE -ne "1" -and
    -not $PytestNarrow -and
    -not $CollectOnly -and
    $NeedsDefaultFlags -and
    $PreflightScope
) {
    $PreflightScript = Join-Path $ScriptDir "pretest_guardrails.ps1"
    if (Test-Path $PreflightScript) {
        Write-Host "[run_pytest] running pretest guardrails (scope=$PreflightScope)"
        $env:BIOETL_PREFLIGHT_ACTIVE = "1"
        try {
            $PreflightArgs = @("--mode", "auto", "--scope", $PreflightScope)
            if ($env:BIOETL_PREFLIGHT_STRICT_DOCS -eq "1") {
                $PreflightArgs += "--strict-docs"
            }
            & $PreflightScript @PreflightArgs
            if ($LASTEXITCODE -ne 0) {
                exit $LASTEXITCODE
            }
            $env:BIOETL_PREFLIGHT_DONE = "1"
        } finally {
            $env:BIOETL_PREFLIGHT_ACTIVE = "0"
        }
    }
}

$QuietRequested = $false
foreach ($Arg in $PytestArgs) {
    if ($Arg -in @("-q", "--quiet", "-qq", "-qqq")) {
        $QuietRequested = $true
    }
}

if ($NeedsDefaultFlags) {
    if ($PytestNarrow -or $CollectOnly) {
        $PytestArgs = @("-q", "--maxfail=1") + $PytestArgs
    } else {
        $PytestArgs = @("--cov=src/bioetl", "--cov-report=term", "-q", "--maxfail=1") + $PytestArgs
    }
}

if ($env:BIOETL_PYTEST_LIVE_OUTPUT -eq "1" -and -not $QuietRequested) {
    $PytestArgs = @($PytestArgs | Where-Object { $_ -ne "-q" })
    $PytestArgs += @("-o", "console_output_style=progress")
}

if ((Test-CoveragePluginNeeded -Args $PytestArgs) -and -not $env:COVERAGE_FILE) {
    $CoverageDir = Join-Path $env:TEMP "bioetl-coverage"
    New-Item -ItemType Directory -Force -Path $CoverageDir | Out-Null
    $env:COVERAGE_FILE = Join-Path $CoverageDir (".coverage.{0}.sqlite" -f $PID)
}

$PytestPluginArgs = @()
if ($PytestNarrow) {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    $PluginModules = @(
        "anyio.pytest_plugin",
        "pytest_asyncio.plugin",
        "_hypothesis_pytestplugin",
        "pytest_timeout",
        "syrupy",
        "pytest_vcr"
    )
    foreach ($Plugin in $PluginModules) {
        $PytestPluginArgs += @("-p", $Plugin)
    }
    if (Test-BenchmarkPluginNeeded -Args $PytestArgs) {
        $PytestPluginArgs += @("-p", "pytest_benchmark.plugin")
    }
} elseif ($env:BIOETL_PYTEST_AUTOLOAD -ne "1") {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    $PluginModules = @(
        "pytest_asyncio.plugin",
        "pytest_timeout",
        "syrupy",
        "pytest_vcr",
        "_hypothesis_pytestplugin"
    )
    if (Test-CoveragePluginNeeded -Args $PytestArgs) {
        $PluginModules += "pytest_cov.plugin"
    }
    if (Test-XdistPluginNeeded -Args $PytestArgs) {
        $PluginModules += "xdist.plugin"
    }
    foreach ($Plugin in $PluginModules) {
        $PytestPluginArgs += @("-p", $Plugin)
    }
    if (Test-BenchmarkPluginNeeded -Args $PytestArgs) {
        $PytestPluginArgs += @("-p", "pytest_benchmark.plugin")
    }
}

$WindowsVenvPython = Join-Path $RepoRoot ".venv-win/Scripts/python.exe"
if (Test-Path $WindowsVenvPython) {
    & $WindowsVenvPython -m pytest @PytestPluginArgs @PytestArgs
    exit $LASTEXITCODE
}

$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m pytest @PytestPluginArgs @PytestArgs
    exit $LASTEXITCODE
}

if ((Test-Path (Join-Path $RepoRoot ".venv")) -or (Test-Path (Join-Path $RepoRoot ".venv-wsl"))) {
    Write-Host "[run_pytest][hint] A WSL/Linux virtualenv was detected. PowerShell should use .venv-win."
    Write-Host "[run_pytest][hint] Bootstrap it with: .\scripts\engineering\dev\setup_env_windows.ps1"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run python -m pytest @PytestPluginArgs @PytestArgs
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pytest @PytestPluginArgs @PytestArgs
    exit $LASTEXITCODE
}

Write-Error "[run_pytest][error] Python runtime is not available."
Write-Host "[run_pytest][hint] Install dependencies first:"
Write-Host "  .\scripts\engineering\dev\setup_env_windows.ps1"
exit 1
