# BioETL: Bioactivity Data Acquisition Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A585%25-brightgreen)](https://github.com/SatoryKono/BioactivityDataAcquisition2/actions/workflows/tests.yml)
[![Version](https://img.shields.io/badge/version-6.1.0-blue)](CHANGELOG.md)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](.github/SECURITY.md)

**BioETL** is a robust, scalable data engineering framework designed to acquire, normalize, and process bioactivity data
from major public repositories (ChEMBL, PubChem, UniProt, etc.) into a unified, analysis-ready **Delta Lake** warehouse.

______________________________________________________________________

## Key Features

- **Medallion Architecture**: Structured data flow (Bronze -> Silver -> Gold) ensuring data quality and traceability.
- **Delta Lake Core**: ACID transactions, schema enforcement, and time travel capabilities.
- **Resilience**: Built-in circuit breakers, exponential backoff retries, and dead-letter queues (Quarantine).
- **Local-First Design**: In-memory locking, local file storage -- no external services required ([ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md)).
- **Deterministic Writes**: Reproducible outputs and deterministic retries ([ADR-014](docs/02-architecture/decisions/ADR-014-deterministic-writes.md)).
- **Observability by Design**: Metrics, tracing, and logging ports ([ADR-017](docs/02-architecture/decisions/ADR-017-observability-architecture.md)).
- **Unified HTTP Client**: Standardized rate limiting, retry, and telemetry ([ADR-032](docs/02-architecture/decisions/ADR-032-unified-http-client.md)).
- **Strict Governance**: Comprehensive rules for schema evolution, data contracts, and operational procedures.

## Architecture Overview

BioETL follows **Hexagonal Architecture** (Ports & Adapters) with **Domain-Driven Design** patterns:

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACES (CLI)                        │
├─────────────────────────────────────────────────────────────┤
│                    COMPOSITION (DI)                         │
│              bootstrap_pipeline() → Factories               │
├─────────────────────────────────────────────────────────────┤
│                     APPLICATION                             │
│         PipelineRunner → Executor → BaseTransformer         │
├─────────────────────────────────────────────────────────────┤
│                       DOMAIN (DDD)                          │
│     Ports │ Aggregates │ Value Objects │ Entities │ Schemas │
├─────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                           │
│    ChEMBL │ PubChem │ UniProt │ Delta Lake │ Observability  │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**: External API -> Bronze (JSONL+zstd) -> Silver (Delta Lake) -> Gold (Analytics)

### Domain Layer (DDD)

The domain layer implements Domain-Driven Design patterns:

| Component         | Description                                                        |
| ----------------- | ------------------------------------------------------------------ |
| **Ports**         | Protocol interfaces for dependency inversion (`domain/ports/`)     |
| **Aggregates**    | Domain aggregates with invariant protection (`domain/aggregates/`) |
| **Value Objects** | Immutable domain primitives (`domain/value_objects/`)              |
| **Entities**      | Domain entities per provider (`domain/entities/`)                  |
| **Schemas**       | Pydantic models for data validation (`domain/schemas/`)            |

## Supported Providers

| Provider             | Entity Types                                                                                                                             | Status     | Rate Limit   |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------ |
| **ChEMBL**           | Activity, Assay, Molecule, Target, Target Component, Protein Class, Cell Line, Compound Record, Publication, Publication Term/Similarity, Subcellular Fraction, Tissue | Production | 3 req/sec    |
| **PubChem**          | Compound                                                                                                                                 | Production | 5 req/sec    |
| **UniProt**          | Protein, ID Mapping                                                                                                                      | Production | 10 req/sec (100 req/sec with API key) |
| **PubMed**           | Publication                                                                                                                              | Production | 3 req/sec    |
| **CrossRef**         | Publication                                                                                                                              | Production | Polite pool  |
| **OpenAlex**         | Publication                                                                                                                              | Production | ~10 req/sec  |
| **Semantic Scholar** | Publication                                                                                                                              | Production | 0.1 req/sec (1 req/sec with API key) |

## Documentation

| Document                                                  | Description                                 |
| --------------------------------------------------------- | ------------------------------------------- |
| [API Reference](docs/04-reference/api/index.md)           | Full API documentation with mkdocstrings    |
| [Architecture Decisions](docs/02-architecture/decisions/) | 43 ADRs explaining design choices           |
| [Ubiquitous Language](docs/00-project/glossary.md)        | Domain terminology and canonical naming     |
| [RULES.md](docs/00-project/RULES.md)                      | Canonical active governance and requirements |
| [Project Map](docs/00-project/00-map.md)                  | Primary navigator for active project docs   |
| [Tools Hub](docs/00-project/TOOLS.md)                     | Current tool entry points and placement rules |
| [CLI Reference](docs/04-reference/cli.md)                 | Command-line interface documentation        |
| [Operations Runbooks](docs/05-operations/runbooks/)       | Incident response and procedures            |
| [Archive Index](docs/99-archive/README.md)                | Historical context only; not normative      |

Start with [Project Map](docs/00-project/00-map.md), [RULES.md](docs/00-project/RULES.md),
and [Tools Hub](docs/00-project/TOOLS.md) for current guidance. Materials under
[`docs/99-archive/`](docs/99-archive/README.md) are preserved for traceability,
but active docs in `docs/00-05` remain the source of truth.

## Quick Start

### Prerequisites

- **Python**: Version 3.11 or higher.
- **Make**: For running automation commands.
- **uv**: Recommended package manager ([install](https://docs.astral.sh/uv/getting-started/installation/)).
- **Docker**: Optional, only for `docker-compose` extras such as Neo4j and monitoring; not required for the Local-Only runtime.
- **Node.js**: Optional, for Mermaid diagram rendering and related docs tooling.

### Installation

#### Option A: Automated Setup (Recommended)

Use the `scripts/dev/dev_setup.sh` script for a complete automated setup:

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition2.git
cd BioactivityDataAcquisition2
./scripts/dev/dev_setup.sh
```

The script will:

- Check required prerequisites (Python 3.11+, Git, Make, uv) and optional extras (Docker, Node.js)
- Create virtual environment and install dependencies
- Set up pre-commit hooks
- Configure environment variables and create data directories
- Detect AI tools (Claude Code, Codex) and sync plugins
- Run verification checks with a summary table

Available modes:

| Flag | Description |
| ---- | ----------- |
| `--quick` / `-q` | Fast install, skip tests and linters |
| `--skip-tests` | Run linters but skip test suite |
| `--force` / `-f` | Recreate virtual environment from scratch |
| `--ci` | CI mode: no colors, non-interactive |
| `--verbose` / `-v` | Show detailed dependency installation output |
| `--no-color` | Disable colored output (also via `NO_COLOR=1`) |

Environment variables: `BIOETL_SKIP_PRECOMMIT=1`, `BIOETL_SKIP_DOCKER=1`.

#### Option B: Manual Setup

1. **Clone and Install**:
   Initialize the virtual environment and install project dependencies.

   ```bash
   git clone https://github.com/SatoryKono/BioactivityDataAcquisition2.git
   cd BioactivityDataAcquisition2
   make install
   ```

1. **Configure Environment** *(optional)*:
   Copy the example configuration if you need API keys for providers.

   ```bash
   cp .env.example .env
   ```

   *Note: Secrets follow the pattern `BIOETL_{PROVIDER}_{KEY}`. For local development, the defaults are usually sufficient.*

   **Environment Variables:**

   | Variable | Description | Default |
   | --- | --- | --- |
   | **Core** | | |
   | `BIOETL_ENV` | Environment (`dev` / `staging` / `prod`) | `dev` |
   | `BIOETL_DATA_DIR` | Base directory for Bronze/Silver/Gold data | `data` |
   | `BIOETL_DEBUG` | Enable debug features | `false` |
   | `BIOETL_TEST_MODE` | Use fixtures instead of real APIs | `false` |
   | **Pipeline** | | |
   | `BIOETL_PIPELINE__BATCH_SIZE` | Records per batch write (1–10000) | `100` |
   | `BIOETL_PIPELINE__CHECKPOINT_INTERVAL` | Save checkpoint every N records (≥100) | `1000` |
   | `BIOETL_PIPELINE__MAX_CONCURRENT_BATCHES` | Max concurrent batch writes (1–16) | `4` |
   | `BIOETL_PIPELINE__HEARTBEAT_INTERVAL` | Lock heartbeat interval in seconds (5–60) | `20` |
   | **Provider API Keys** | | |
   | `BIOETL_UNIPROT_API_KEY` | UniProt API key (higher rate limits) | — |
   | `BIOETL_PUBMED_API_KEY` | NCBI E-utilities API key | — |
   | `BIOETL_PUBMED_EMAIL` | Email for NCBI tool identification | — |
   | `BIOETL_OPENALEX_EMAIL` | Email for OpenAlex polite pool | — |
   | `BIOETL_SEMANTICSCHOLAR_API_KEY` | Semantic Scholar API key | — |
   | `BIOETL_CROSSREF_EMAIL` | Email for Crossref polite pool | — |
   | **Security** | | |
   | `BIOETL_PII_SALT_CURRENT` | Salt for PII hashing (≥32 chars, required in prod) | — |
   | `BIOETL_PII_SALT_NEXT` | Next salt for rotation | — |
   | `BIOETL_SALT_ROTATION_ACTIVE` | Whether salt rotation is active | `false` |
   | **Observability** | | |
   | `BIOETL_LOG_LEVEL` | Logging level (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`) | `INFO` |
   | `BIOETL_LOG_FORMAT` | Log format (`json` / `text`) | `json` |
   | `BIOETL_LOG_FILE` | Log file path | `logs/bioetl.log` |
   | `BIOETL_METRICS_ENABLED` | Enable Prometheus metrics | `true` |
   | `BIOETL_METRICS_PORT` | Prometheus HTTP server port | `8000` |
   | `BIOETL_OBSERVABILITY__TRACING_ENABLED` | Enable OpenTelemetry tracing | `false` |
   | `BIOETL_OBSERVABILITY__DQ_MONITOR_ENABLED` | Enable data quality monitoring | `false` |
   | **Data Quality** | | |
   | `BIOETL_DQ_SOFT_THRESHOLD` | Warning error rate threshold | `0.05` |
   | `BIOETL_DQ_HARD_THRESHOLD` | Fail batch error rate threshold | `0.20` |
   | **Resilience** | | |
   | `BIOETL_CB_FAILURE_THRESHOLD` | Consecutive errors to open circuit breaker | `5` |
   | `BIOETL_CB_RECOVERY_TIMEOUT` | Circuit breaker recovery timeout (seconds) | `300` |
   | `BIOETL_RETRY_MAX_ATTEMPTS` | Maximum retry attempts | `3` |
   | `BIOETL_RETRY_MULTIPLIER` | Exponential backoff multiplier | `2.0` |
   | **Delta Lake** | | |
   | `BIOETL_DELTA_VACUUM_RETENTION` | VACUUM retention (days) | `7` |
   | `BIOETL_DELTA_FORENSIC_RETENTION` | Forensic retention (days) | `7` |
   | **Quarantine** | | |
   | `BIOETL_QUARANTINE_RETENTION_DAYS` | Quarantine record retention (days) | `30` |
   | `BIOETL_QUARANTINE_PAYLOAD_MAX_SIZE` | Max payload size (bytes) | `65536` |

   See [`.env.example`](.env.example) for the full list with comments.

1. **Verify Installation**:
   Run tests to ensure everything works.

   ```bash
   make lint && make test
   ```

> **Note**: BioETL uses local file storage by default (`data/` directory). No Docker or external services required. See [Local Storage Layout](docs/03-guides/local-storage-layout.md) and [ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md) for details.

### Running Pipelines

Activate the virtual environment:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

Run the ETL pipeline using the CLI:

```bash
# Run incremental update for ChEMBL
bioetl run --pipeline chembl_activity --run-type incremental

# Run backfill with resume capability
bioetl run --pipeline chembl_activity --run-type backfill --resume

# Inspect quarantined records
bioetl quarantine inspect --pipeline chembl_activity --limit 10

# List checkpoints
bioetl checkpoint list
```

## Development

### Repository Hygiene

- Do **not** store domain datasets or reference data files in repository root.
- Keep machine-consumed reference datasets under semantic paths in `data/` (for example, `data/input/reference/`).
- Keep optional human-facing spreadsheet copies under `docs/04-reference/schemas/` when they are needed for documentation.
- Unified publication classifier canonical format is CSV at `data/input/reference/unified_classification.csv`; optional spreadsheet copies are non-canonical and MAY be stored in docs as needed.
### Local diagnostic artifacts

Локальные диагностические файлы (например, `git_commit_*.txt`, `*_gitshow_err.txt`, `log_test.txt`) не должны храниться в корне репозитория и не коммитятся в Git.

* Временные диагностические дампы сохраняйте в `tmp/`.
* Логи локальных запусков сохраняйте в `logs/`.
* Для ad-hoc команд используйте явное перенаправление (`> logs/<name>.log 2>&1` или `> tmp/<name>.txt 2>&1`).

### MCP Setup (GitHub Copilot + Codex)

To configure the GitHub MCP server for both VS Code Copilot and Codex CLI:

```bash
./scripts/dev/setup_copilot_codex_mcp.sh
```

Windows PowerShell:

```powershell
.\scripts\dev\setup_copilot_codex_mcp.ps1
```

What this script does:

- Writes workspace MCP config for Copilot at `.vscode/mcp.json`.
- Registers `github` MCP server in Codex CLI if it is not already configured.
- Does **not** store tokens in repository files.

Before using GitHub MCP tools, set a token in your shell:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="<your_pat>"
```

### Testing

The project uses `pytest` for testing, split into Unit, Integration, and Architecture tests.

- **Setup Plugins (pytest + pre-commit):**

  ```bash
  make setup-plugins
  ```

  This command validates required pytest plugins and installs pre-commit hooks.

- **Quick Check (with dependencies auto-synced and coverage):**

  ```bash
  ./scripts/run_pytest.sh
  ```

  The helper bootstraps the virtual environment (installs `pytest-cov`, `orjson`, `syrupy`, and other test-only dependencies) and reproduces the default CI command with coverage output.

  If you prefer to run the command manually, activate the local virtual environment first to avoid `--cov` argument errors:

  ```bash
  source .venv/bin/activate
  # Install test extras so pytest-asyncio/pytest-cov options are available
  pip install -e ".[dev,tests]"
  python -m pytest tests --cov=src/bioetl --cov-report=term
  ```

  With `uv`, the equivalent is:

  ```bash
  uv sync --extra dev --extra tests
  uv run python -m pytest tests --cov=src/bioetl --cov-report=term
  ```

  To include tracing and pre-commit plugin setup:

  ```bash
  uv sync --extra dev --extra tests --extra tracing
  uv run python -m pre_commit install --install-hooks
  ```

  Если `pytest` сообщает об отсутствии обязательных плагинов (`pytest-asyncio`, `pytest-cov`), выполните повторную синхронизацию:

  ```bash
  uv sync --extra dev --extra tests --extra tracing
  ```

  Скрипт `./scripts/run_pytest.sh` проверяет наличие плагинов и автоматически доустанавливает их при необходимости.

- **Run All Tests**:

  ```bash
  make test
  ```

- **Run Unit Tests Only** (Fast, no I/O):

  ```bash
  make test-unit
  ```

- **Run Integration Tests** (Uses VCR.py cassettes, no network required):

  ```bash
  make test-integration
  ```

- **Run Architecture Tests**:

  ```bash
  make test-architecture
  ```

### Codex Skills

- **Sync project skills into Codex**:

  ```bash
  make setup-skills
  ```

  This syncs local project skills from `.codex/skills` into `$CODEX_HOME/skills` (default `~/.codex/skills`).

### Code Quality

Strict quality standards are enforced using `ruff`, `mypy`, and other tools.

- **Linting & Formatting**:
  ```bash
  make lint      # Check only
  make lint-fix  # Auto-fix and format
  ```
- **Type Checking**:
  ```bash
  make typecheck # Strict mypy
  ```
- **Complexity Check**:
  ```bash
  make complexity
  ```

### Documentation

Build and serve local documentation:

```bash
make docs-serve
```

Access the docs at `http://localhost:8000`.

## Project Structure

```
.
├── configs/                  # YAML pipeline configurations
├── docs/                     # Documentation (Architecture, Guides, Runbooks)
│   ├── 02-architecture/      # Layer docs, diagrams, ADRs (43 decisions)
│   ├── 00-project/
│   │   ├── glossary.md       # Ubiquitous Language glossary
│   │   └── RULES.md          # Project governance (v5.23)
│   └── ...
├── src/
│   └── bioetl/
│       ├── domain/           # Pure business logic (DDD), NO I/O
│       │   ├── ports/        # Protocol interfaces (Ports)
│       │   ├── aggregates/   # DDD Aggregates with invariants
│       │   ├── value_objects/ # Immutable domain primitives
│       │   ├── entities/     # Domain entities per provider
│       │   ├── schemas/      # Pydantic/Pandera validation schemas
│       │   └── exceptions/   # Classified exceptions (Critical/Recoverable/DQ)
│       ├── application/      # Pipeline orchestration & services
│       │   ├── core/         # PipelineRunner, Executor, BaseTransformer
│       │   ├── pipelines/    # ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, Semantic Scholar (+ common utilities)
│       │   └── services/     # Application services (lifecycle, vacuum, cleanup)
│       ├── composition/      # Composition Root (DI, bootstrap)
│       │   ├── factories/    # Pipeline, storage, data source factories
│       │   └── providers/    # Provider registry
│       ├── infrastructure/   # Adapters (API clients, Delta Lake, Storage)
│       │   ├── adapters/     # HTTP clients with unified resilience
│       │   ├── storage/      # Bronze/Silver/Gold writers
│       │   ├── locking/      # In-memory locks (MemoryLock)
│       │   └── observability/ # Metrics, tracing, logging
│       └── interfaces/       # External interfaces
│           ├── cli/          # Click CLI commands
│           └── orchestration/ # Reserved (empty; signal handlers removed 2025-12-31, shutdown logic in application/core/shutdown.py)
├── tests/                    # Unit, Integration, Architecture & E2E tests
├── scripts/                  # Utility scripts (lint_terminology.py, etc.)
├── Makefile                  # Automation commands
└── pyproject.toml            # Dependencies & Tool configuration
```

### Root layout policy

Repository root is protected by `scripts/audit_root_cleanliness.py` (pre-commit + CI job `root-hygiene`).
Only approved top-level entries are allowed.

**Core allowed root entries**:

- Source and tests: `src/`, `tests/`
- Documentation and references: `docs/`, `README.md`, `CHANGELOG.md`
- Build/configuration: `pyproject.toml`, `uv.lock`, `Makefile`, `.pre-commit-config.yaml`, `.github/`
- Operational/project assets: `configs/`, `scripts/`, `assets/`, `data/`, `reports/`, `grafana/`
- Legacy tracked root artifacts listed in the allowlist inside `scripts/audit_root_cleanliness.py`

**Where to place artifacts**:

- Test artifacts and run reports → `reports/`
- Logs and diagnostic dumps → `reports/` (or nested folder by run date/provider)
- Coverage artifacts (`coverage.xml`, `htmlcov/`, `.coverage*`) → keep out of git, generate locally/CI only
- Reference datasets and static lookup files → `docs/` (documentation reference) or `data/` (runtime/local data)

## Local-Only Deployment

BioETL uses a strictly Local-Only runtime model defined by
[ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md).
Active workflows use filesystem-backed checkpoints, local storage, and
in-memory locking. Distributed deployment, Redis locking, and Docker-based
runtime orchestration are not supported entry points for current development or
operations.

## Security

Please review our **[Security Policy](.github/SECURITY.md)** for:

- Threat model and trust boundaries
- Secret management guidelines
- Data validation architecture
- Vulnerability reporting process

## Contributing

Please read **[RULES.md](docs/00-project/RULES.md)** before contributing.

1. Ensure all tests pass: `make test`
1. Check types and linting: `make lint`
1. Follow the **RFC 2119** keywords in requirements.

## License

This project is licensed under the MIT License.
