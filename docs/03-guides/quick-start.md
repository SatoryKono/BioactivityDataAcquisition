______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-19'

______________________________________________________________________

# Quick Start

TL;DR for setting up and running BioETL locally.

> **Note**: BioETL использует **Local-Only** deployment (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) не требуются.
>
> **Boundary**: this page is the fastest supported bootstrap path. For the full
> onboarding walkthrough, environment/config details, and broader first-time
> troubleshooting, use [Getting Started](getting-started.md). If you
> intentionally use optional Docker helper stacks, see
> [Docker Quick Start](../DOCKER_QUICKSTART.md) and
> [Docker Setup](../DOCKER_SETUP.md); they are adjunct tooling, not the
> canonical application bootstrap path.

## Runtime compatibility policy

- **Python runtime baseline: 3.12**.
- **Source of truth**: `pyproject.toml` (`requires-python`, classifiers).
- Treat any Python 3.10/3.11 snippets as deprecated and update to 3.12 commands.

## Setup (3 minutes)

### Option A: Supported Local Bootstrap (Recommended)

```bash
# Clone and enter directory
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Install dependencies and create/refresh the local environment
uv sync --extra dev --extra tests --extra tracing

# Configure pytest + pre-commit tooling
uv run python -m scripts.ops setup-plugins
```

Canonical bootstrap uses `uv sync` / `make install` / `python -m scripts.ops setup-plugins`. `scripts/engineering/dev/dev_setup.sh` was **removed** and is not a supported path.

`uv` is the preferred package/environment manager for supported bootstrap and
docs verification flows. `pip` remains the fallback only when `uv` is
unavailable.

### Option B: Mixed Windows + WSL Checkout

If you open the same repository from both Windows PowerShell and WSL, keep the
environments separate:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
bash scripts/engineering/dev/run_mypy.sh
```

This bootstrap creates `.venv-win` for PowerShell and
`${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` for WSL/Linux by default.
The supported Windows default is `-n 1`; raise
`BIOETL_PYTEST_WINDOWS_XDIST_WORKERS` only when you have verified the machine
can sustain more workers without `WinError 10055`.

### Option C: Manual Fallback

```bash
# Clone and enter directory
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Preferred manual path without make
uv sync --extra dev --extra tracing

# Fallback without uv: use an installed Python 3.12+ interpreter.
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,tracing]"
```

If you need MkDocs/site tooling, install the separate docs toolchain as well:

```bash
uv sync --extra dev --extra tracing --extra docs
# or, without uv:
pip install -e ".[dev,tracing,docs]"
```

## Run Your First Pipeline

```bash
# CI / single-OS checkout
uv run python -m bioetl run --pipeline chembl_activity --limit 100 --no-cached-bronze

# WSL mixed checkout
"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m bioetl run --pipeline chembl_activity --limit 100 --no-cached-bronze

# Windows PowerShell mixed checkout
.\.venv-win\Scripts\python.exe -m bioetl run --pipeline chembl_activity --limit 100 --no-cached-bronze

# Console-script form also works after the environment is activated:
bioetl run --pipeline chembl_activity --limit 100 --no-cached-bronze

# Data will be stored in:
# - data/output/bronze/chembl/activity/
# - data/output/silver/chembl/activity/
# - data/output/gold/chembl/activity/ (only for pipelines with Gold enabled)
```

## Verify

```bash
# Stable local suite with coverage gate
uv run python -m scripts.engineering.dev run-tests cov

# WSL mixed-checkout wrappers
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
bash scripts/engineering/dev/run_mypy.sh

# Check linting / typing
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
```

```powershell
# PowerShell mixed-checkout wrappers
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

## Common Commands

| Task                     | Command                                                               |
| ------------------------ | --------------------------------------------------------------------- |
| Install dependencies     | `uv sync --extra dev --extra tests --extra tracing`                   |
| Mixed-checkout bootstrap | `setup_env_windows.ps1` / `setup_env_wsl.sh`                          |
| Configure plugins        | `uv run python -m scripts.ops setup-plugins`                          |
| Verify dependencies      | `uv run python -m scripts.engineering.dev run-tests smoke`            |
| Run tests via wrappers   | `run_pytest.ps1` / `run_pytest.sh`                                    |
| Run all tests            | `uv run python -m scripts.engineering.dev run-tests cov`              |
| Run linting              | `uv run ruff check . && uv run ruff format --check . && uv run mypy src tests` |
| Verify docs surface      | `uv run python -m scripts.docs check-links --links --specs --configs` |
| Run sample pipeline      | `uv run python -m bioetl run --pipeline chembl_activity --limit 10 --no-cached-bronze` |
| List pipelines           | `bioetl config list-pipelines`                                        |
| Full rebuild             | `bioetl run --pipeline <name> --run-type rebuild`                     |
| Resume from checkpoint   | `bioetl run --pipeline <name> --resume`                               |

## Project Structure (Data)

```text
data/
└── output/
    ├── bronze/          # Raw API responses (JSONL + zstd)
    ├── silver/          # Cleaned Delta Lake tables
    ├── gold/            # Aggregated/enriched tables
    ├── checkpoints/     # Pipeline state for resume
    └── quarantine/      # Failed records for review
```

## Next Steps

- [Getting Started](getting-started.md) - Full setup guide with troubleshooting
- [Running Pipelines](running-pipelines.md) - Pipeline execution workflows and runtime control flow
- [Docs Verification](docs-verification.md) - Published docs quality gates and recurring audit checklist
- [Add New Source](add-new-source.md) - Integrate a new data provider
- [Guides Index](index.md) - Browse the full how-to surface
