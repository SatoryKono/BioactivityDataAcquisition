# Getting Started Guide

This guide will walk you through setting up a complete local development environment for BioETL. By the end of this guide, you will have a running instance of the platform and be able to execute data pipelines.

> **Note**: BioETL использует **Local-Only** deployment (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) не требуются.

## Prerequisites

Ensure you have the following tools installed on your machine:

- **Python 3.11** or higher: [Download](https://www.python.org/downloads/)
- **Git**: Version control.
- **Make** (optional): Build automation tool. On Windows, use Chocolatey or WSL, or run commands manually.

**Not required:**

- Docker Desktop (Local-Only architecture)
- Redis, MinIO, Postgres (replaced with local file system and in-memory locks)

## 1. Clone the Repository

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition2.git
cd BioactivityDataAcquisition2
```

## 2. Environment Setup

The supported setup path is the maintained Make-based bootstrap:

```bash
make install
make test-deps
make setup-plugins
```

If you use Codex or GitHub Copilot MCP, add the optional tooling setup after install:

```bash
python -m scripts.dev setup-mcp
```

`scripts/dev/dev_setup.sh` remains in the repository as a legacy placeholder and is not the supported onboarding path.

Manual fallback without `make`:

```bash
uv sync --extra dev --extra tracing
```

On Windows without `make` or `uv`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,tracing]
```

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

If you plan to access APIs requiring authentication (e.g., UniProt, OpenAlex), add your keys to `.env`:

```ini
BIOETL_UNIPROT_API_KEY=your-key-here
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

If all tests pass, your environment is ready!

## 5. Running Your First Pipeline

To verify the end-to-end flow, run a sample pipeline (e.g., ChEMBL Activity).

```bash
# Ensure your virtual environment is active
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Run the pipeline
bioetl run --pipeline chembl_activity --limit 100
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
    ├── checkpoints/
    │   └── chembl_activity.json
    └── quarantine/
        └── common.quarantine/
```

## Troubleshooting

### "Make command not found"

On Windows, ensure you have installed Make via Chocolatey (`choco install make`) or use the manual commands listed above.

### Permission Denied on data/

Ensure the `data/` directory is writable. On Linux/macOS: `chmod -R 755 data/`

### Tests Fail with "VCR cassette not found"

Run tests with `--vcr-record=once` to record new cassettes, or ensure you're running against the existing fixtures.

### Pipeline Fails with "Lock already held"

Another pipeline instance may be running. Check for zombie Python processes or wait for the current pipeline to complete.

## Next Steps

- [Running Pipelines](running-pipelines.md) - Comprehensive guide to pipeline execution
- [Add New Source](add-new-source.md) - Integrate a new data provider
- [Project Navigator](../00-project/00-map.md) - Full documentation index
- [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md) - Architecture decision details
