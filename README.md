# BioETL: Bioactivity Data Acquisition Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A585%25-brightgreen)](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/workflows/tests.yml)
[![Version](https://img.shields.io/badge/version-5.14.0-blue)](CHANGELOG.md)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](SECURITY.md)

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
| **ChEMBL**           | Activity, Assay, Molecule, Target, Target Component, Protein Class, Cell Line, Compound Record, Publication, Publication Term/Similarity | Production | None         |
| **PubChem**          | Compound                                                                                                                                 | Production | 5 req/sec    |
| **UniProt**          | Protein, ID Mapping                                                                                                                      | Production | 100 req/sec  |
| **PubMed**           | Publication                                                                                                                              | Production | 3 req/sec    |
| **CrossRef**         | Publication                                                                                                                              | Production | Polite pool  |
| **OpenAlex**         | Publication                                                                                                                              | Production | ~10 req/sec  |
| **Semantic Scholar** | Publication                                                                                                                              | Production | 100 req/5min |

## Documentation

| Document                                                  | Description                                 |
| --------------------------------------------------------- | ------------------------------------------- |
| [API Reference](docs/04-reference/api/index.md)           | Full API documentation with mkdocstrings    |
| [Architecture Decisions](docs/02-architecture/decisions/) | 34 ADRs explaining design choices           |
| [Ubiquitous Language](docs/00-project/glossary.md)        | Domain terminology and canonical naming     |
| [RULES.md](docs/00-project/RULES.md)                      | Project governance and requirements (v5.19) |
| [Project Map](docs/00-project/00-map.md)                  | Documentation navigator and code map        |
| [CLI Reference](docs/04-reference/cli.md)                 | Command-line interface documentation        |
| [Operations Runbooks](docs/05-operations/runbooks/)       | Incident response and procedures            |

## Quick Start

### Prerequisites

- **Python**: Version 3.11 or higher.
- **Make**: For running automation commands.
- **Docker**: Optional, legacy-only (see [Legacy Distributed Mode](#legacy-distributed-mode-rejected--unsupported)).

### Installation

#### Option A: Automated Setup (Recommended)

Use the `dev_setup.sh` script for a complete automated setup:

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
./dev_setup.sh
```

The script will:

- Check prerequisites (Python 3.11+, Git, Make)
- Create virtual environment and install dependencies
- Set up pre-commit hooks
- Configure environment variables
- Run verification checks

For quick setup without tests: `./dev_setup.sh --quick`

#### Option B: Manual Setup

1. **Clone and Install**:
   Initialize the virtual environment and install project dependencies.

   ```bash
   git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
   cd BioactivityDataAcquisition
   make install
   ```

1. **Configure Environment** *(optional)*:
   Copy the example configuration if you need API keys for providers.

   ```bash
   cp .env.example .env
   ```

   *Note: Secrets follow the pattern `BIOETL_{PROVIDER}_{KEY}`.*

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
- Keep optional human-facing spreadsheet copies under `docs/reference/`.
- Unified publication classifier canonical format is CSV at `data/input/reference/unified_classification.csv`; Excel is optional documentation copy at `docs/reference/unified_classification.xlsx`.

### Local diagnostic artifacts

Локальные диагностические файлы (например, `git_commit_*.txt`, `*_gitshow_err.txt`, `log_test.txt`) не должны храниться в корне репозитория и не коммитятся в Git.

- Временные диагностические дампы сохраняйте в `tmp/`.
- Логи локальных запусков сохраняйте в `logs/`.
- Для ad-hoc команд используйте явное перенаправление (`> logs/<name>.log 2>&1` или `> tmp/<name>.txt 2>&1`).

### Testing

The project uses `pytest` for testing, split into Unit, Integration, and Architecture tests.

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
  make arch-test
  ```

- **Verify Gold contract parity (blocking CI gate):**

  ```bash
  uv run python src/tools/verify_schema_parity.py
  ```

  Gate semantics:

  - **Blocking failures**: parity diff, PK coverage break, nullable break.
  - **Warnings (non-blocking)**: additive non-breaking nullable fields.

  Changelog classification template for schema changes:

  - **MAJOR**: remove/rename fields, type tightening, non-null tightening.
  - **MINOR**: additive nullable fields.
  - **PATCH**: descriptions/examples/docs-only updates.

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
│   ├── 02-architecture/      # Layer docs, diagrams, ADRs (34 decisions)
│   ├── 00-project/
│   │   ├── glossary.md       # Ubiquitous Language glossary
│   │   └── RULES.md          # Project governance (v5.19)
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
├── dev_setup.sh              # Automated development environment setup
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

## Legacy Distributed Mode (REJECTED / UNSUPPORTED)

> **CRITICAL WARNING**: Distributed deployment and Redis Locking are **STRICTLY PROHIBITED** by [ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md).
> The instructions below are for historical reference only and must NOT be used for new deployments.

For distributed deployments with Redis locking and S3-compatible storage, you can use Docker Compose:

```bash
# Start infrastructure services (Postgres, Redis, MinIO)
make docker-up

# Run E2E tests with Docker
make test-e2e

# Stop services
make docker-down
```

> **Decision**: We have officially abandoned Redis Locks in favor of a strictly Local-Only architecture.

## Security

Please review our **[Security Policy](SECURITY.md)** for:

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
