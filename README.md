# BioETL: Bioactivity Data Acquisition Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Version](https://img.shields.io/badge/version-5.0.0-blue)](CHANGELOG.md)
[![Status: Active Development](https://img.shields.io/badge/Status-Active%20Development%20(55%25)-yellow)](IMPLEMENTATION_ROADMAP.md)

**BioETL** is a robust, scalable data engineering framework designed to acquire, normalize, and process bioactivity data
from major public repositories (ChEMBL, PubChem, UniProt, etc.) into a unified, analysis-ready **Delta Lake** warehouse.

---

## 🚀 Key Features

* **Medallion Architecture**: Structured data flow (Bronze → Silver → Gold) ensuring data quality and traceability.
* **Delta Lake Core**: ACID transactions, schema enforcement, and time travel capabilities.
* **Resilience**: Built-in circuit breakers, exponential backoff retries, and dead-letter queues (Quarantine).
* **Concurrency Control**: Distributed locking with Redis to prevent race conditions during backfills.
* **Strict Governance**: Comprehensive rules for schema evolution, data contracts, and operational procedures.

## ⚡ Quick Start

### Prerequisites

* **Python**: Version 3.11 or higher.
* **Docker**: Required for local infrastructure (Postgres, Redis, MinIO).
* **Make**: For running automation commands.

### Installation

1. **Clone and Install**:
   Initialize the virtual environment and install project dependencies.
   ```bash
   git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
   cd BioactivityDataAcquisition
   make install
   ```

2. **Configure Environment**:
   Copy the example configuration.
   ```bash
   cp .env.example .env
   ```
   *Note: Secrets follow the pattern `BIOETL_{PROVIDER}_{KEY}`.*

3. **Start Infrastructure**:
   Launch local services (Postgres, Redis, MinIO) via Docker Compose.
   ```bash
   make docker-up
   ```

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

* **Run All Tests**:
  ```bash
  make test
  ```
* **Run Unit Tests Only** (Fast, no I/O):
  ```bash
  make test-unit
  ```
* **Run Integration Tests** (Uses Docker/VCR.py):
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
├── configs/             # YAML pipeline configurations
├── docs/                # Documentation (Architecture, Guides, Runbooks)
├── src/
│   └── bioetl/
│       ├── domain/      # Pure business logic & interfaces (Ports)
│       ├── application/ # Pipeline orchestration & services
│       ├── infrastructure/ # Adapters (API clients, Delta Lake, Redis)
│       └── cli.py       # Command-line interface entry point
├── tests/               # Unit, Integration & Architecture tests
├── .env.example         # Environment variables template
├── Makefile             # Automation commands
├── pyproject.toml       # Dependencies & Tool configuration
└── README.md            # Project documentation
```

## 🤝 Contributing

Please read **[RULES.md](docs/RULES.md)** before contributing.

1. Ensure all tests pass: `make test`
2. Check types and linting: `make lint`
3. Follow the **RFC 2119** keywords in requirements.

## 📄 License

This project is licensed under the MIT License.
