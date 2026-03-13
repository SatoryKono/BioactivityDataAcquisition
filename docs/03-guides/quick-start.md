# Quick Start

TL;DR for setting up and running BioETL locally.

> **Note**: BioETL использует **Local-Only** deployment (ADR-010).
> Docker и внешние сервисы (Redis, MinIO) не требуются.

## Setup (3 minutes)

### Option A: Automated (Recommended)

```bash
# Clone and enter directory
git clone https://github.com/SatoryKono/BioactivityDataAcquisition2.git
cd BioactivityDataAcquisition2

# Full automated setup (checks prereqs, installs deps, configures env)
./scripts/dev/dev_setup.sh

# Or quick setup without tests:
# ./scripts/dev/dev_setup.sh --quick

# CI-friendly (no colors, non-interactive):
# ./scripts/dev/dev_setup.sh --ci
```

### Option B: Manual Fallback

```bash
# Clone and enter directory
git clone https://github.com/SatoryKono/BioactivityDataAcquisition2.git
cd BioactivityDataAcquisition2

# Install dependencies manually (fallback path)
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
# Note: Use --no-cached-bronze for the very first run to fetch from API
bioetl run --pipeline chembl_activity --limit 100 --no-cached-bronze

# Data will be stored in:
# - data/output/bronze/chembl/activity/
# - data/output/silver/chembl/activity/
# - data/output/gold/chembl/activity/ (only for pipelines with Gold enabled)
```

## Verify

```bash
# Run tests
make test

# Check linting
make lint
```

## Common Commands

| Task                   | Command                                           |
| ---------------------- | ------------------------------------------------- |
| Install dependencies   | `./scripts/dev/dev_setup.sh`                      |
| Verify dependencies    | `make test-deps`                                  |
| Run all tests          | `make test`                                       |
| Run linting            | `make lint`                                       |
| Run on fixtures        | `make run-local`                                  |
| List pipelines         | `bioetl config list-pipelines`                    |
| Full rebuild           | `bioetl run --pipeline <name> --run-type rebuild` |
| Resume from checkpoint | `bioetl run --pipeline <name> --resume`           |

## Project Structure (Data)

```text
data/
└── output/
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
