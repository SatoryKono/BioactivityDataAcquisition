# BioETL: Bioactivity Data Acquisition Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready%20(v5.0)-green)](docs/RULES.md)

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

* Python 3.11+
* Docker & Docker Compose (for local infrastructure)
* Make

### Installation

1. **Clone and Install**:
   ```bash
   git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
   cd BioactivityDataAcquisition
   make install
   ```

2. **Start Infrastructure** (Postgres, Redis, MinIO):
   ```bash
   make docker-up
   ```

3. **Run a Pipeline** (Example: ChEMBL Activity):
   ```bash
   # Activate virtual environment
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows

   # Run pipeline
   python -m bioetl.main run --pipeline chembl_activity
   ```

## 📚 Documentation

The project documentation is organized as follows:

* **[Project Rules (RULES.md)](docs/RULES.md)**: The "Constitution" of the project. Contains all architectural
  decisions, coding standards, and operational policies. **Start here.**
* **[Changelog](CHANGELOG.md)**: History of changes and versioning.
* **[Developer Guides](docs/03-guides/quick-start.md)**: Detailed setup and development instructions.
* **[Architecture](docs/02-architecture/system-context.md)**: System design and data flow diagrams.

To view the full documentation site locally:

```bash
pip install -e .[docs]
mkdocs serve
```

## 🛠 Project Structure

```
.
├── configs/             # YAML pipeline configurations
├── docs/                # Documentation (Architecture, Guides, Runbooks)
├── src/
│   └── bioetl/
│       ├── domain/      # Pure business logic & interfaces (Ports)
│       ├── application/ # Pipeline orchestration & services
│       └── infrastructure/ # Adapters (API clients, Delta Lake, Redis)
├── tests/               # Unit & Integration tests (VCR.py)
├── RULES.md             # Governance & Standards (v5.0)
├── Makefile             # Automation commands
└── pyproject.toml       # Dependencies & Tool configuration
```

## 🤝 Contributing

Please read **[RULES.md](docs/RULES.md)** before contributing.

1. Ensure all tests pass: `make test`
2. Check types and linting: `make lint`
3. Follow the **RFC 2119** keywords in requirements.

## 📄 License

This project is licensed under the MIT License.
