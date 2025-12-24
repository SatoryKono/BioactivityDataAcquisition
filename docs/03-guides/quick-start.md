# Quick Start

TL;DR for setting up and running BioETL locally.

> **Note**: BioETL использует **Local-Only** deployment (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) не требуются.

## Setup (3 minutes)

```bash
# Clone and enter directory
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Install dependencies (creates venv, installs packages)
make install

# Optional: Configure environment
cp .env.example .env
```

## Run Your First Pipeline

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Run ChEMBL activity pipeline (limited to 100 records)
python -m bioetl.main run --pipeline chembl_activity --limit 100

# Data will be stored in:
# - data/bronze/v1/chembl/activity/
# - data/silver/chembl.activity/
# - data/gold/chembl.activity_gold/
```

## Verify

```bash
# Run tests
make test

# Check linting
make lint
```

## Common Commands

| Task | Command |
|------|---------|
| Install dependencies | `make install` |
| Run all tests | `make test` |
| Run linting | `make lint` |
| Run on fixtures | `make run-local` |
| List pipelines | `python -m bioetl.main list` |
| Full rebuild | `python -m bioetl.main run --pipeline <name> --full-rebuild` |
| Resume from checkpoint | `python -m bioetl.main run --pipeline <name> --resume` |

## Project Structure (Data)

```
data/
├── bronze/          # Raw API responses (JSONL + zstd)
├── silver/          # Cleaned Delta Lake tables
├── gold/            # Aggregated/enriched tables
├── checkpoints/     # Pipeline state for resume
└── quarantine/      # Failed records for review
```

## Next Steps

- [Getting Started](getting-started.md) - Full setup guide with troubleshooting
- [Running Pipelines](running-pipelines.md) - Comprehensive CLI reference
- [Add New Source](add-new-source.md) - Integrate a new data provider
