______________________________________________________________________

Version: 1.2.3
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-30'

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

Baseline Local-Only setup requires only the following local tools:

- **Python 3.12** (baseline): [Download](https://www.python.org/downloads/)
- **uv** (recommended): Python package/environment manager used by the maintained install path.
- **Git**: Version control.
- **Make** (optional): Build automation tool. On Windows, use Chocolatey or WSL, or run commands manually.

**Optional adjunct tooling only, not baseline prerequisites:**

- Docker Desktop
- Redis, MinIO, Postgres helper stacks

## Runtime compatibility policy

- **Python runtime baseline: 3.12** for onboarding and local execution.
- **Source of truth**: `pyproject.toml` (`requires-python`, Trove classifiers).
- Any references to Python 3.10/3.11 are deprecated documentation drift and should be ignored.

## 1. Clone the Repository

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
```

## 2. Environment Setup

The supported setup path depends on how you use the checkout.

### 2.1. CI / Single-OS Checkout

Use the canonical **operator** aggregate (see [`Makefile`](../../Makefile)
`install` / `test-deps` / `setup-plugins`):

```bash
make install
make test-deps
make setup-plugins
```

`make install` is the wrapper around lock-backed `uv sync` (extras are defined
on that target, not copied here). `make setup-plugins` calls
`python -m scripts.ops setup-plugins`
([`scripts/ops/__main__.py`](../../scripts/ops/__main__.py)).

If you use Codex or GitHub Copilot MCP, add the optional tooling setup after install:

```bash
uv run python -m scripts.engineering.dev setup-mcp
```

If you activated `.venv` instead of using `uv`, `python -m scripts.engineering.dev setup-mcp`
is also valid.

`scripts/engineering/dev/dev_setup.sh` is **not present**
([`scripts/engineering/dev/README.md`](../../scripts/engineering/dev/README.md));
do not invoke it.

### 2.2. Mixed Windows + WSL Checkout

If you use the same repository from both Windows PowerShell and WSL, bootstrap
each OS separately instead of sharing one `.venv`:

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

This path creates `.venv-win` for PowerShell and
`${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` for WSL/Linux by default.
Keep the PowerShell wrapper at `-n 1` unless you intentionally raise
`BIOETL_PYTEST_WINDOWS_XDIST_WORKERS`; Windows mixed-checkout runs otherwise
hit the known socket-buffer ceiling sooner than WSL/Linux.

### 2.3. Manual Fallback

Manual fallback when you do not use the recommended bootstrap helper:

```bash
uv sync --extra dev --extra tests --extra tests_full --extra export
```

If you need MkDocs/site tooling, install the separate docs toolchain extra on
top of the canonical bootstrap extras:

```bash
uv sync --extra dev --extra tests --extra tests_full --extra export --extra docs
```

On Windows without `make` or `uv`, use the repository Python 3.12 baseline:

```powershell
py -3.12 -m venv .venv-win
.\.venv-win\Scripts\Activate.ps1
pip install -e ".[dev,tests,tests_full,export]"
```

For the supported aggregate setup flow, use `make install`, `make test-deps`,
and `make setup-plugins`. `make install` is lock-backed `uv sync` with extras
`dev`, `tests`, `tests_full`, and `export` (see the `install` target in
[`Makefile`](../../Makefile)). Coverage and architecture verify paths need
`tests_full`; do not omit it from a manual fallback. The repository-local
`scripts/engineering/dev/dev_setup.sh` is absent
([`scripts/engineering/dev/README.md`](../../scripts/engineering/dev/README.md));
do not invoke it.

## 3. Configuration

### Environment Variables

Copy the example environment file to create your local configuration:

```bash
cp .env.example .env
```

Open `.env` and verify the settings. For local development, the defaults are usually sufficient.
AI/runtime agents must not create or edit `.env` files without explicit
per-task approval; this command is a human local setup step.

**Key Variables:**

- `BIOETL_ENV`: Set to `dev`.
- `BIOETL_DATA_DIR`: Directory for data storage (default: `./data`).
- `BIOETL_LOG_LEVEL`: Logging level (default: `INFO`).

> **Note:** For a complete reference of all BIOETL_* environment variables, see [Environment Variables Reference](../04-reference/environment-variables.md).

### Secrets

If you plan to access APIs requiring authentication, or optional higher-limit provider modes, add your keys to `.env`:

```ini
BIOETL_UNIPROT_API_KEY=your-optional-key-here
BIOETL_OPENALEX_API_KEY=your-openalex-key-here
BIOETL_OPENALEX_EMAIL=your-email@example.com
```

`BIOETL_UNIPROT_API_KEY` is optional because UniProt uses public access by
default. `BIOETL_OPENALEX_API_KEY` is required for production-like OpenAlex
runs; `BIOETL_OPENALEX_EMAIL` is optional attribution metadata.

## 4. Verify Installation

We recommend running a quick smoke lane before the full test suite to ensure
critical runtime packages are available.

```bash
uv run python -m scripts.engineering.dev run-tests smoke
```

Then run the full test suite:

```bash
uv run python -m scripts.engineering.dev run-tests cov
```

For mixed-checkout day-to-day verification, prefer the OS-specific wrappers:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
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

Ensure the `data/` directory is writable by the BioETL process owner only.
On Linux/macOS use least-privilege access, not world-readable modes:

```bash
chmod -R u+rwX,go-rwx data/
```

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
