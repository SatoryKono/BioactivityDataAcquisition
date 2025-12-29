# BioETL: Bioactivity Data Acquisition Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Version](https://img.shields.io/badge/version-5.0.0-blue)](CHANGELOG.md)
[![Status: Active Development](https://img.shields.io/badge/Status-Active%20Development%20(55%25)-yellow)](IMPLEMENTATION_ROADMAP.md)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](SECURITY.md)

**BioETL** is a robust, scalable data engineering framework designed to acquire, normalize, and process bioactivity data
from major public repositories (ChEMBL, PubChem, UniProt, etc.) into a unified, analysis-ready **Delta Lake** warehouse.

---

## 🚀 Key Features

* **Medallion Architecture**: Structured data flow (Bronze → Silver → Gold) ensuring data quality and traceability.
* **Delta Lake Core**: ACID transactions, schema enforcement, and time travel capabilities.
* **Resilience**: Built-in circuit breakers, exponential backoff retries, and dead-letter queues (Quarantine).
* **Local-First Design**: In-memory locking, local file storage — no external services required ([ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md)).
* **Strict Governance**: Comprehensive rules for schema evolution, data contracts, and operational procedures.

## 🏗 Architecture Overview

BioETL follows **Hexagonal Architecture** (Ports & Adapters) with clear layer separation:

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACES (CLI)                        │
├─────────────────────────────────────────────────────────────┤
│                    COMPOSITION (DI)                         │
│              bootstrap_pipeline() → Factories               │
├─────────────────────────────────────────────────────────────┤
│                     APPLICATION                             │
│         PipelineRunner → Executor → Transformer             │
├─────────────────────────────────────────────────────────────┤
│                       DOMAIN                                │
│              Ports (Interfaces) │ Types │ Entities          │
├─────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                           │
│         ChEMBL │ PubChem │ Delta Lake │ Observability       │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**: External API → Bronze (JSONL+zstd) → Silver (Delta Lake) → Gold (Analytics)

## 📊 Supported Providers

| Provider | Entity Types | Status | Rate Limit |
|----------|-------------|--------|------------|
| **ChEMBL** | Activity, Assay, Molecule, Target, Document | Production | None |
| **PubChem** | Compound | Production | 5 req/sec |
| **UniProt** | Protein | Production | 100 req/sec |
| **PubMed** | Publication | Production | 3 req/sec |

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/04-reference/api/index.md) | Full API documentation with mkdocstrings |
| [Architecture Decisions](docs/02-architecture/decisions/) | ADRs explaining design choices |
| [RULES.md](docs/RULES.md) | Project governance and requirements |
| [CLI Reference](docs/04-reference/cli.md) | Command-line interface documentation |
| [Operations Runbooks](docs/05-operations/runbooks/) | Incident response and procedures |

## ⚡ Quick Start

### Prerequisites

* **Python**: Version 3.11 or higher.
* **Make**: For running automation commands.
* **Docker**: *Optional* — only for legacy distributed mode (see [Legacy Setup](#legacy-distributed-mode-optional)).

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

2. **Configure Environment** *(optional)*:
   Copy the example configuration if you need API keys for providers.
   ```bash
   cp .env.example .env
   ```
   *Note: Secrets follow the pattern `BIOETL_{PROVIDER}_{KEY}`.*

3. **Verify Installation**:
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

## 🛠 Development

### Testing

The project uses `pytest` for testing, split into Unit, Integration, and Architecture tests.

* **Quick Check (with dependencies auto-synced and coverage):**
  ```bash
  ./scripts/run_pytest.sh
  ```
  The helper bootstraps the virtual environment (installs `pytest-cov`, `orjson`, `syrupy`, and other test-only dependencies) and reproduces the default CI command with coverage output.

* **Run All Tests**:
  ```bash
  make test
  ```
* **Run Unit Tests Only** (Fast, no I/O):
  ```bash
  make test-unit
  ```
* **Run Integration Tests** (Uses VCR.py cassettes, no network required):
  ```bash
  make test-integration
  ```
* **Run Architecture Tests**:
  ```bash
  make arch-test
  ```

### Code Quality

Strict quality standards are enforced using `ruff`, `mypy`, and other tools.

* **Linting & Formatting**:
  ```bash
  make lint      # Check only
  make lint-fix  # Auto-fix and format
  ```
* **Type Checking**:
  ```bash
  make typecheck # Strict mypy
  ```
* **Complexity Check**:
  ```bash
  make complexity
  ```

### Documentation

Build and serve local documentation:

```bash
make docs-serve
```

Access the docs at `http://localhost:8000`.

## 📂 Project Structure

```
.
├── configs/                  # YAML pipeline configurations
├── docs/                     # Documentation (Architecture, Guides, Runbooks)
├── src/
│   └── bioetl/
│       ├── domain/           # Pure business logic & interfaces (Ports)
│       ├── application/      # Pipeline orchestration & services
│       │   ├── core/         # Base pipeline, executor, shutdown
│       │   └── pipelines/    # Concrete pipelines (ChEMBL, etc.)
│       ├── composition/      # Composition Root (DI, bootstrap)
│       │   └── factories/    # Pipeline factories
│       ├── infrastructure/   # Adapters (API clients, Delta Lake, Storage)
│       │   ├── adapters/     # HTTP clients (ChEMBL, PubChem, UniProt)
│       │   ├── storage/      # Bronze/Silver/Gold writers (local filesystem)
│       │   └── locking/      # In-memory locks (MemoryLock)
│       └── interfaces/       # External interfaces
│           ├── cli.py        # Click CLI entry point
│           └── orchestration/ # Runner, signals, Prefect
├── tests/                    # Unit, Integration & Architecture tests
├── .env.example              # Environment variables template
├── dev_setup.sh              # Automated development environment setup
├── Makefile                  # Automation commands
├── pyproject.toml            # Dependencies & Tool configuration
└── README.md                 # Project documentation
```

## 🐳 Legacy Distributed Mode (REJECTED / UNSUPPORTED)

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

## 🔒 Security

Please review our **[Security Policy](SECURITY.md)** for:
- Threat model and trust boundaries
- Secret management guidelines
- Data validation architecture
- Vulnerability reporting process

## 🤝 Contributing

Please read **[RULES.md](docs/RULES.md)** before contributing.

1. Ensure all tests pass: `make test`
2. Check types and linting: `make lint`
3. Follow the **RFC 2119** keywords in requirements.

## 📄 License

This project is licensed under the MIT License.
