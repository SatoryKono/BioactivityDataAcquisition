# ============================================================
# BioETL Test Runner (PowerShell)
# Usage: .\scripts\dev\run_tests.ps1 <command> [pytest-args...]
# ============================================================
param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1, ValueFromRemainingArguments)]
    [string[]]$ExtraArgs = @()
)

$ErrorActionPreference = "Stop"

# --- Colors ---
function Write-Info  { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Ok    { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Err   { Write-Host "[FAIL] $args" -ForegroundColor Red }

function Show-Usage {
    @"
BioETL Test Runner

Usage: .\scripts\dev\run_tests.ps1 <command> [pytest-args...]

Commands:
  all           Run all tests (stop on first failure)
  unit          Unit tests only (tests/unit/)
  arch          Architecture tests (tests/architecture/)
  integration   Integration tests (tests/integration/)
  contract      Contract tests (tests/contract/)
  contract-live Contract tests with live APIs + network enabled
  smoke         Smoke tests (tests/smoke/)
  security      Security tests (tests/security/)
  cov           All tests with coverage report (fail-under=85%)
  quick         Unit + smoke (fast feedback loop)
  parallel      All tests via pytest-xdist (-n auto)
  marker <m>    Run tests by marker, e.g.: marker slow
  failed        Re-run only failed tests from last run
  file <path>   Run a specific test file
  help          Show this message

Options:
  Any extra arguments are passed directly to pytest.

Examples:
  .\scripts\dev\run_tests.ps1 unit
  .\scripts\dev\run_tests.ps1 unit -k "test_transformer"
  .\scripts\dev\run_tests.ps1 cov --cov-report=term-missing
  .\scripts\dev\run_tests.ps1 marker hypothesis
  .\scripts\dev\run_tests.ps1 file tests/unit/domain/test_entities.py -v
"@
}

function Invoke-Pytest {
    param(
        [string]$Label,
        [string[]]$PytestArgs
    )
    Write-Info "Running: $Label"
    Write-Info "Command: py -m pytest $($PytestArgs -join ' ')"
    Write-Host ""
    py -m pytest @PytestArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Ok "$Label passed"
    } else {
        Write-Host ""
        Write-Err "$Label failed"
        exit $LASTEXITCODE
    }
}

switch ($Command) {
    "all" {
        Invoke-Pytest "All Tests" (@("tests/", "-x", "-q") + $ExtraArgs)
    }
    "unit" {
        Invoke-Pytest "Unit Tests" (@("tests/unit/", "-x", "-q") + $ExtraArgs)
    }
    "arch" {
        Invoke-Pytest "Architecture Tests" (@("tests/architecture/", "-v") + $ExtraArgs)
    }
    "integration" {
        Invoke-Pytest "Integration Tests" (@("tests/integration/", "-x", "-q") + $ExtraArgs)
    }
    "contract" {
        Invoke-Pytest "Contract Tests" (@("tests/contract/", "-v") + $ExtraArgs)
    }
    "contract-live" {
        $prevLive = $env:BIOETL_LIVE_API_TESTS
        $prevNetwork = $env:BIOETL_NETWORK_TESTS
        try {
            $env:BIOETL_LIVE_API_TESTS = "true"
            $env:BIOETL_NETWORK_TESTS = "true"
            Invoke-Pytest "Contract Tests (live)" (@("tests/contract/", "--network", "-v") + $ExtraArgs)
        } finally {
            $env:BIOETL_LIVE_API_TESTS = $prevLive
            $env:BIOETL_NETWORK_TESTS = $prevNetwork
        }
    }
    "smoke" {
        Invoke-Pytest "Smoke Tests" (@("tests/smoke/", "-v") + $ExtraArgs)
    }
    "security" {
        Invoke-Pytest "Security Tests" (@("tests/security/", "-v") + $ExtraArgs)
    }
    "cov" {
        Invoke-Pytest "Tests + Coverage" (@(
            "tests/",
            "--cov=src/bioetl",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=85",
            "-q"
        ) + $ExtraArgs)
        Write-Ok "HTML report: htmlcov/index.html"
    }
    "quick" {
        Write-Info "Quick check: unit + smoke"
        Invoke-Pytest "Unit Tests"  (@("tests/unit/", "-x", "-q") + $ExtraArgs)
        Invoke-Pytest "Smoke Tests" (@("tests/smoke/", "-x", "-q") + $ExtraArgs)
    }
    "parallel" {
        Invoke-Pytest "All Tests (parallel)" (@("tests/", "-n", "auto", "-q") + $ExtraArgs)
    }
    "marker" {
        if ($ExtraArgs.Count -lt 1) {
            Write-Err "Usage: .\run_tests.ps1 marker <marker-name> [pytest-args...]"
            exit 1
        }
        $m = $ExtraArgs[0]
        $rest = if ($ExtraArgs.Count -gt 1) { $ExtraArgs[1..($ExtraArgs.Count-1)] } else { @() }
        Invoke-Pytest "Marker: $m" (@("tests/", "-m", $m, "-v") + $rest)
    }
    "failed" {
        Invoke-Pytest "Re-run Failed" (@("tests/", "--lf", "-x", "-v") + $ExtraArgs)
    }
    "file" {
        if ($ExtraArgs.Count -lt 1) {
            Write-Err "Usage: .\run_tests.ps1 file <path> [pytest-args...]"
            exit 1
        }
        $f = $ExtraArgs[0]
        $rest = if ($ExtraArgs.Count -gt 1) { $ExtraArgs[1..($ExtraArgs.Count-1)] } else { @() }
        Invoke-Pytest "File: $f" (@($f, "-v") + $rest)
    }
    { $_ -in "help", "--help", "-h" } {
        Show-Usage
    }
    default {
        Write-Err "Unknown command: $Command"
        Show-Usage
        exit 1
    }
}
