# Welcome to BioETL

This is the central documentation hub for the BioETL project.

## Project Mission

To build a robust, scalable, and maintainable data pipeline for acquiring and processing bioactivity data from various public sources into a unified, analysis-ready format.

## Quick Links

*   [**Project Navigator**](00-map.md): Full documentation map with links to all resources.
*   [**Project Rules**](RULES.md): The constitution of our project. All contributions **MUST** adhere to these rules.
*   [**Quick Start Guide**](03-guides/quick-start.md): Get your local development environment up and running in minutes.
*   [**Architecture Overview**](02-architecture/system-context.md): Understand the high-level design and data flow.
*   [**How-To Guides**](03-guides/): Guides for common tasks (adding sources, pipelines, troubleshooting).

## Key Features

| Feature | Description | ADR |
|---------|-------------|-----|
| **Medallion Architecture** | Bronze → Silver → Gold data flow | [ADR-002](02-architecture/decisions/ADR-002-medallion-architecture.md) |
| **Delta Lake Storage** | ACID transactions, time travel, schema evolution | [ADR-001](02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) |
| **Local-Only Deployment** | File-based storage, no Docker/Redis required | [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md) |
| **Graceful Shutdown** | SIGTERM/SIGINT handling with checkpoint save | [ADR-008](02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) |
| **Circuit Breaker** | Fault tolerance for API failures | [ADR-007](02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) |
| **Deterministic Writes** | Reproducible SCD2 with ingestion_ts | [ADR-014](02-architecture/decisions/ADR-014-deterministic-writes.md) |
| **Gold Validation** | Pandera strict schema validation | [ADR-018](02-architecture/decisions/ADR-018-gold-strict-validation.md) |

## Supported Providers

| Provider | Entities | Status |
|----------|----------|--------|
| **ChEMBL** | Activity, Assay, Molecule, Target, Target Component, Document | Production |
| **PubChem** | Compound | Production |
| **UniProt** | Protein | Production |
| **PubMed** | Publication | Production |

## Current Version

**v5.3.3** (2025-12-26) — See [CHANGELOG](CHANGELOG.md) for details.

## Getting Started

```bash
# Clone and setup
git clone <repo-url>
cd BioactivityDataAcquisition2
make install

# Run a pipeline
bioetl run --pipeline chembl_activity --limit 100

# Run tests
make test
```

---

*Last updated: 2025-12-26*
