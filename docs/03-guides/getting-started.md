______________________________________________________________________

Version: 1.2.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-04'

______________________________________________________________________

# Getting Started Guide

This guide walks through setting up a complete local development environment for
BioETL. By the end, you will have a working local runtime/tooling environment
and be able to execute data pipelines.

> **Note**: BioETL использует **Local-Only** deployment (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) не требуются.
>
> **Boundary**: use [Quick Start](quick-start.md) if you only need the shortest
> supported bootstrap path and a first smoke run. This page remains the fuller
> onboarding walkthrough.

## Prerequisites

Ensure you have the following tools installed on your machine:

- **Python 3.11** or higher: [Download](https://www.python.org/downloads/)
- **uv** (recommended): Python package/environment manager used by the maintained install path.
- **Git**: Version control.
- **Make** (optional): Build automation tool. On Windows, use Chocolatey or WSL, or run commands manually.

**Not required:**

- Docker Desktop
- Redis, MinIO, Postgres

## 1. Clone the Repository

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
```

## 2. Environment Setup

The supported setup path depends on how you use the checkout.

### 2.1. CI / Single-OS Checkout

Use the maintained Make-based bootstrap:

```bash
make install
make test-deps
make setup-plugins
```

If you use Codex or GitHub Copilot MCP, add the optional tooling setup after install:

```bash
uv run python -m scripts.engineering.dev setup-mcp
```

If you activated `.venv` instead of using `uv`, `python -m scripts.engineering.dev setup-mcp`
is also valid.

`scripts/engineering/dev/dev_setup.sh` remains in the repository as a legacy placeholder and is not the supported onboarding path.

### 2.2. Mixed Windows + WSL Checkout

If you use the same repository from both Windows PowerShell and WSL, bootstrap
each OS separately instead of sharing one `.venv`:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 4 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n 4 --lf
bash scripts/engineering/dev/run_mypy.sh
```

This path creates `.venv-win` for PowerShell and
`${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` for WSL/Linux by default.

### 2.3. Manual Fallback Without `make`

Manual fallback without `make`:

```bash
uv sync --extra dev --extra tracing
```

If you need MkDocs or `make docs-build`, install the separate docs toolchain extra:

```bash
uv sync --extra dev --extra tracing --extra docs
```

On Windows without `make` or `uv`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,tracing,docs]
```

If you prefer the convenience aggregate target, `make setup-dev` is still valid;
it currently expands to `make install` plus dependency verification. The
repository-local `scripts/engineering/dev/dev_setup.sh` is not part of the supported path.

## 3. Configuration

### Environment Variables

Copy the example environment file to create your local configuration:

```bash
cp .env.example .env
```

Open `.env` and verify the settings. For local development, the defaults are usually sufficient.

**Key Variables:**

- `BIOETL_ENV`: Set to `dev`.
- `BIOETL_DATA_DIR`: Directory for data storage (default: `./data`).
- `BIOETL_LOG_LEVEL`: Logging level (default: `INFO`).

### Secrets

If you plan to access APIs requiring authentication, or optional higher-limit provider modes, add your keys to `.env`:

```ini
BIOETL_UNIPROT_API_KEY=your-optional-key-here
BIOETL_OPENALEX_API_KEY=your-openalex-key-here
BIOETL_OPENALEX_EMAIL=your-email@example.com
```

## 4. Verify Installation

We recommend running a dependency check before starting the full test suite to ensure all critical runtime packages (`pandas`, `pandera`, `polars`, etc.) are correctly installed.

```bash
make test-deps
```

Then run the full test suite:

```bash
make test
```

For mixed-checkout day-to-day verification, prefer the OS-specific wrappers:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 4 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n 4 --lf
bash scripts/engineering/dev/run_mypy.sh
```

If all tests pass, your environment is ready!

For published docs checks, drift review, and the strict site-build path, use
the dedicated [Docs Verification](docs-verification.md) guide instead of
copying ad-hoc commands from older notes.

## 5. Running Your First Pipeline

To verify the end-to-end flow, run a sample pipeline (e.g., ChEMBL Activity).

```bash
# CI / single-OS checkout
uv run python -m bioetl run --pipeline chembl_activity --limit 100

# WSL mixed checkout
"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m bioetl run --pipeline chembl_activity --limit 100

# Windows PowerShell mixed checkout
.\.venv-win\Scripts\python.exe -m bioetl run --pipeline chembl_activity --limit 100
```

This command will:

1. Fetch 100 records from the ChEMBL API.
1. Save raw data to the **Bronze** layer (`data/output/bronze/chembl/activity/`).
1. Normalize and save to the **Silver** layer (`data/output/silver/chembl/activity/`).
1. Aggregate to the **Gold** layer (`data/output/gold/chembl/activity/`).

## Data Directory Structure

After running a pipeline, your data directory will look like:

```text
data/
└── output/
    ├── bronze/
    │   └── chembl/activity/
    │       └── batch-001.jsonl.zst
    ├── silver/
    │   └── chembl/activity/
    │       └── _delta_log/
    ├── gold/
    │   └── chembl/activity/
    │       └── _delta_log/
    ├── control/
    │   ├── run_manifest/
    │   └── run_ledger/
    ├── checkpoints/
    │   └── chembl_activity.json
    └── quarantine/
        └── common.quarantine/
```

## Troubleshooting

### "Make command not found"

On Windows, ensure you have installed Make via Chocolatey (`choco install make`) or use the manual commands listed above.

### "The environment works in WSL but not in PowerShell" (or vice versa)

Do not reuse the same `.venv` across Windows and WSL. Use
`.venv-win` in PowerShell and `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` in
WSL via `setup_env_windows.ps1` / `setup_env_wsl.sh`.

### Permission Denied on data/

Ensure the `data/` directory is writable. On Linux/macOS: `chmod -R 755 data/`

### Tests Fail with "VCR cassette not found"

Run tests with `--vcr-record=new_episodes` to record missing cassette interactions intentionally, or ensure you're running against the existing fixtures in strict replay mode.

### Pipeline Fails with "Lock already held"

Another pipeline instance may be running. Check for zombie Python processes or wait for the current pipeline to complete.

## Next Steps

- [Running Pipelines](running-pipelines.md) - Comprehensive guide to pipeline execution
- [GitHub Local Workflow](github-local-workflow.md) - Local branch, verify, and PR routine
- [Add New Source](add-new-source.md) - Integrate a new data provider
- [Guides Index](index.md) - Browse the full how-to surface
- [Project Navigator](../00-project/00-map.md) - Full documentation index
- [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md) - Architecture decision details
