# Welcome to BioETL

This is the central documentation hub for the BioETL project.

## Project Mission

To build a robust, scalable, and maintainable data pipeline for acquiring and processing bioactivity data from various public sources into a unified, analysis-ready format.

## Quick Links

- [**Documentation Index**](00-map.md): Structured navigation for all documentation.
- [**Quick Reference**](rules-summary.md): Key rules at a glance.
- [**Project Navigator**](00-map.md): Full documentation map with links to all resources.
- [**Project Rules**](RULES.md): The constitution of our project (SSOT). All contributions **MUST** adhere to these rules.
- [**Quick Start Guide**](../03-guides/quick-start.md): Get your local development environment up and running in minutes.
- [**Architecture Overview**](../02-architecture/system-context.md): Understand the high-level design and data flow.
- [**How-To Guides**](../03-guides/): Guides for common tasks (adding sources, pipelines, troubleshooting).

## Key Features

| Feature                    | Description                                          | ADR                                                                               |
| -------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Medallion Architecture** | Bronze → Silver → Gold data flow                     | [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md)         |
| **Delta Lake Storage**     | ACID transactions, time travel, schema evolution     | [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)          |
| **Local-Only Deployment**  | File-based storage, no Docker/Redis required         | [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)          |
| **Graceful Shutdown**      | SIGTERM/SIGINT handling with checkpoint save         | [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)     |
| **Circuit Breaker**        | Fault tolerance for API failures                     | [ADR-007](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) |
| **Deterministic Writes**   | Reproducible SCD2 with ingestion-ts                  | [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md)           |
| **Gold Validation**        | Pandera strict schema validation                     | [ADR-018](../02-architecture/decisions/ADR-018-gold-strict-validation.md)         |
| **Composite Pipeline**     | Multi-source data enrichment (seed → enrich → merge) | [ADR-026](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)     |

## Supported Providers (7)

| Provider            | Entities                                                                    | Status     | Rate Limit   |
| ------------------- | --------------------------------------------------------------------------- | ---------- | ------------ |
| **ChEMBL**          | Activity, Assay, Molecule, Target, Target Component, Document (13 entities) | Production | None         |
| **PubChem**         | Compound                                                                    | Production | 5 req/sec    |
| **UniProt**         | Protein                                                                     | Production | 100 req/sec  |
| **PubMed**          | Publication                                                                 | Production | 3 req/sec    |
| **CrossRef**        | Publication                                                                 | Production | Polite pool  |
| **OpenAlex**        | Publication                                                                 | Production | 10 req/sec   |
| **SemanticScholar** | Publication                                                                 | Production | 100 req/5min |

### Composite Pipeline (ADR-026)

BioETL supports multi-source data enrichment through Composite Pipelines:

```bash
# Run composite publication pipeline (seed from ChEMBL, enrich from CrossRef, OpenAlex, PubMed)
bioetl run --pipeline composite_publication --limit 1000
```

See [Composite Pipeline Diagram](../02-architecture/mmd-diagrams/foundation/29-composite-pipeline-workflow.mmd) for workflow visualization.

## Current Version

**v6.0.0** (2026-02-18) — See [CHANGELOG](https://github.com/SatoryKono/BioactivityDataAcquisition2/blob/main/CHANGELOG.md) and [Release Notes](https://github.com/SatoryKono/BioactivityDataAcquisition2/blob/main/CHANGELOG.md#600---2026-02-18) for details.

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

----------------------------------------------------------------------

*Last updated: 2026-02-24*
