#!/usr/bin/env pwsh
# BioETL Environment Setup Script for Windows
# This script sets up the complete development environment for BioETL on Windows.
# Run with: .\setup.ps1

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

function Write-Section {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Gray
}

# Get script directory and repo root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir ".")

Write-Section "BioETL Windows Environment Setup"
Write-Info "Repository root: $RepoRoot"

# Set UV environment variables
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

# Check for conflicting venv
if ((Test-Path (Join-Path $RepoRoot ".venv")) -and -not (Test-Path (Join-Path $RepoRoot ".venv/Scripts/python.exe"))) {
    Write-Warning "Found a non-Windows .venv. It will be ignored in favor of .venv-win."
}

# Step 1: Check prerequisites
Write-Section "Step 1: Checking Prerequisites"

$HasUv = Get-Command uv -ErrorAction SilentlyContinue
$HasPython = Get-Command python -ErrorAction SilentlyContinue
$HasPy = Get-Command py -ErrorAction SilentlyContinue

if (-not $HasUv -and -not $HasPython -and -not $HasPy) {
    Write-Error "Neither uv, python, nor py is available. Please install Python 3.12+ or uv."
    exit 1
}

if ($HasUv) {
    Write-Success "Found uv package manager"
} elseif ($HasPy) {
    Write-Success "Found py launcher"
} else {
    Write-Success "Found python"
}

# Step 2: Create virtual environment
Write-Section "Step 2: Creating Virtual Environment"

if ($HasUv) {
    Write-Info "Creating venv with uv (Python 3.13)..."
    Invoke-CheckedCommand -Command { uv venv $VenvDir --python 3.13 --allow-existing } -ErrorMessage "uv venv failed."
} else {
    if (-not (Test-Path $VenvPython)) {
        if ($HasPy) {
            Write-Info "Creating venv with py launcher (Python 3.13)..."
            Invoke-CheckedCommand -Command { py -3.13 -m venv $VenvDir } -ErrorMessage "py -3.13 -m venv failed."
        } else {
            Write-Info "Creating venv with python..."
            Invoke-CheckedCommand -Command { python -m venv $VenvDir } -ErrorMessage "python -m venv failed."
        }
    } else {
        Write-Info "Reusing existing .venv-win"
    }
}

Write-Success "Virtual environment ready at $VenvDir"

# Step 3: Install dependencies
Write-Section "Step 3: Installing Dependencies"

if ($HasUv) {
    Write-Info "Syncing dependencies with uv (dev + tracing extras)..."
    $env:VIRTUAL_ENV = $VenvDir
    $env:PATH = "$VenvDir\Scripts;$env:PATH"
    Invoke-CheckedCommand -Command { uv sync --active --extra dev --extra tracing } -ErrorMessage "uv sync failed."
    Write-Info "Tip: If sync fails, retry; UV_HTTP_TIMEOUT defaults to $env:UV_HTTP_TIMEOUT seconds."
} else {
    Write-Info "Bootstrapping pip..."
    Invoke-CheckedCommand -Command { & $VenvPython -m ensurepip --upgrade } -ErrorMessage "ensurepip failed."

    Write-Info "Upgrading pip, setuptools, wheel..."
    Invoke-CheckedCommand -Command { & $VenvPython -m pip install --upgrade pip setuptools wheel } -ErrorMessage "pip bootstrap failed."

    Write-Info "Installing package with dev + tracing extras..."
    Invoke-CheckedCommand -Command { & $VenvPython -m pip install -e ".[dev,tracing]" } -ErrorMessage "editable install failed."
}

Write-Success "Dependencies installed"

# Step 4: Setup pytest plugins
Write-Section "Step 4: Setting Up Pytest Plugins"

$SetupPluginsScript = Join-Path $RepoRoot "scripts\ops\launchers\codex\setup_plugins.sh"
if (Test-Path $SetupPluginsScript) {
    Write-Info "Running setup_plugins.sh (pytest-only mode)..."
    if (Get-Command bash -ErrorAction SilentlyContinue) {
        bash $SetupPluginsScript --pytest-only
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Pytest plugins configured"
        } else {
            Write-Warning "setup_plugins.sh failed, but this may be expected on Windows"
        }
    } else {
        Write-Warning "bash not found; skipping plugin setup. Install Git for Windows to get bash."
    }
} else {
    Write-Warning "setup_plugins.sh not found; skipping plugin setup"
}

# Step 5: Setup pre-commit hooks (optional)
Write-Section "Step 5: Setting Up Pre-Commit Hooks (Optional)"

Write-Info "Installing pre-commit hooks..."
& $VenvPython -m pre_commit install --hook-type pre-commit --hook-type pre-push
if ($LASTEXITCODE -eq 0) {
    Write-Success "Pre-commit hooks installed"
} else {
    Write-Warning "Pre-commit hooks installation failed (optional)"
}

# Step 6: Setup MCP (optional)
Write-Section "Step 6: Setting Up MCP (Optional)"

$SetupMcpScript = Join-Path $RepoRoot "scripts\ai\codex\setup_mcp.py"
if (Test-Path $SetupMcpScript) {
    Write-Info "Running setup_mcp.py..."
    & $VenvPython $SetupMcpScript
    if ($LASTEXITCODE -eq 0) {
        Write-Success "MCP configured"
    } else {
        Write-Warning "MCP setup failed (optional)"
    }
} else {
    Write-Warning "setup_mcp.py not found; skipping MCP setup"
}

# Step 7: Setup Codex skills (optional)
Write-Section "Step 7: Setting Up Codex Skills (Optional)"

$SetupSkillsScript = Join-Path $RepoRoot "scripts\ai\codex\setup_skills.sh"
if (Test-Path $SetupSkillsScript) {
    Write-Info "Running setup_skills.sh..."
    if (Get-Command bash -ErrorAction SilentlyContinue) {
        bash $SetupSkillsScript
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Codex skills synced"
        } else {
            Write-Warning "Codex skills setup failed (optional)"
        }
    } else {
        Write-Warning "bash not found; skipping skills setup"
    }
} else {
    Write-Warning "setup_skills.sh not found; skipping skills setup"
}

# Step 8: Environment configuration
Write-Section "Step 8: Environment Configuration"

$EnvExample = Join-Path $RepoRoot ".env.example"
$EnvFile = Join-Path $RepoRoot ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Info "Copying .env.example to .env..."
    Copy-Item $EnvExample $EnvFile
    Write-Success ".env file created from .env.example"
    Write-Warning "Please edit .env to add your API keys and configuration"
} else {
    Write-Info ".env file already exists; skipping"
}

# Final summary
Write-Section "Setup Complete"

Write-Success "Environment is ready!"
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Activate the virtual environment:" -ForegroundColor White
Write-Host "   .\.venv-win\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "`n2. Run tests:" -ForegroundColor White
Write-Host "   .\scripts\engineering\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf" -ForegroundColor Gray
Write-Host "`n3. Run linting:" -ForegroundColor White
Write-Host "   .\.venv-win\Scripts\python.exe -m ruff check src tests" -ForegroundColor Gray
Write-Host "   .\.venv-win\Scripts\python.exe -m ruff format src tests" -ForegroundColor Gray
Write-Host "`n4. Run type checking:" -ForegroundColor White
Write-Host "   .\scripts\engineering\dev\run_mypy.ps1" -ForegroundColor Gray
Write-Host "`n5. Edit .env to add your API keys (see .env.example for reference)" -ForegroundColor White
Write-Host "`nFor more information, see README.md" -ForegroundColor Gray
