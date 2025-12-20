# Quick Start

TL;DR for setting up and running BioETL locally.

## Setup (5 minutes)

```bash
# Clone and enter directory
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Install dependencies
make install

# Configure environment
cp .env.example .env

# Start infrastructure (Redis, MinIO)
make docker-up
```

## Run Your First Pipeline

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Run ChEMBL activity pipeline (limited to 100 records)
python -m bioetl.main run --pipeline chembl_activity --limit 100
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
| Run all tests | `make test` |
| Run linting | `make lint` |
| Start infrastructure | `make docker-up` |
| Stop infrastructure | `make docker-down` |
| List pipelines | `python -m bioetl.main list` |
| Full rebuild | `python -m bioetl.main run --pipeline <name> --full-rebuild` |

## Next Steps

- [Getting Started](getting-started.md) - Full setup guide with troubleshooting
- [Running Pipelines](running-pipelines.md) - Comprehensive CLI reference
- [Add New Source](add-new-source.md) - Integrate a new data provider
