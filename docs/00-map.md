# BioETL Project Navigator

*Synced with RULES.md v5.6 | Last updated: 2025-12-27*

## Quick Links

| Need to...              | Go to                                                                  |
|-------------------------|------------------------------------------------------------------------|
| Understand the rules    | [00-project_rules/01-project-rules.md](00-project_rules/01-project-rules.md)                 |
| Create a new pipeline   | [00-project_rules/04-extending-bioetl.md](00-project_rules/04-extending-bioetl.md)      |
| Review a pipeline       | [templates/pipeline-review-checklist.md](templates/pipeline-review-checklist.md) |
| Handle a prod error     | [05-operations/runbooks/index.md](05-operations/runbooks/index.md)                           |
| Understand architecture | [02-architecture/system-context.md](02-architecture/system-context.md)                  |
| Check data contracts    | [contracts/gold/activity.json](contracts/gold/activity.json)                                  |

---

## Language Policy

| Category | Language | Examples |
|----------|----------|----------|
| **Public-facing** | English | README.md, CONTRIBUTING.md, CHANGELOG.md |
| **User guides** | English | docs/03-guides/*, docs/04-reference/* |
| **Internal governance** | Russian | RULES.md, AGENT.md, docs/00-project_rules/* |
| **Architecture docs** | Russian | docs/02-architecture/* |
| **Code comments** | Russian | Docstrings, inline comments |

---

## Documentation Structure

```
docs/
├── 00-map.md                    # This file (Project Navigator)
│
├── 00-project_rules/            # Project governance
│   ├── 00-rules-summary.md      # TL;DR of RULES.md
│   ├── 01-project-rules.md      # Full project rules
│   ├── 02-user-rules.md         # Guidelines for contributors
│   ├── 03-file-policy.md        # File/directory structure
│   ├── 04-extending-bioetl.md   # How to add providers/pipelines
│   └── 05-cleanup-policy.md     # Cleanup and retention
│
├── 02-architecture/             # System architecture
│   ├── system-context.md        # C4 System Context Diagram
│   ├── container-diagram.md     # C4 Container Diagram
│   ├── data-flow.md             # High-level Medallion data flow
│   ├── 04-interfaces-layer.md   # Interfaces layer docs
│   ├── 05-composition-layer.md  # Composition layer (DI) docs
│   ├── decisions/               # Architecture Decision Records (ADR-001..020)
│   └── diagrams/                # Diagram source files
│
├── 03-guides/                   # How-to guides
│   ├── quick-start.md           # Quick start guide
│   ├── getting-started.md       # Getting started
│   ├── running-pipelines.md     # Running pipelines
│   ├── troubleshooting.md       # Troubleshooting
│   ├── add-new-source.md        # Adding new data source
│   └── add-pipeline-existing-source.md  # Adding pipeline to existing source
│
├── 04-reference/                # Reference documentation
│
├── 05-operations/               # Operational runbooks
│
├── contracts/                   # Data contracts
│   └── gold/                    # Gold layer contracts
│
└── templates/                   # Document & code templates
    ├── pipeline-review-checklist.md
    ├── config.yaml.tpl
    ├── factory.py.tpl
    ├── pipeline.py.tpl
    └── source_adapter.py.tpl
```

---

## By Topic

### Getting Started

1. [01-project-rules.md](00-project_rules/01-project-rules.md) - Project rules (start here)
2. [00-rules-summary.md](00-project_rules/00-rules-summary.md) - Quick reference
3. [02-user-rules.md](00-project_rules/02-user-rules.md) - Contributor guidelines

### Architecture

| Document                                                                                     | Covers                                   | RULES.md |
|----------------------------------------------------------------------------------------------|------------------------------------------|----------|
| [system-context.md](02-architecture/system-context.md)                                       | Entity models, IDs, relationships        | §2.8     |
| [container-diagram.md](02-architecture/container-diagram.md)                               | C4 Container, Docker services            | §5.6     |
| [data-flow.md](02-architecture/data-flow.md)                                                 | Ports & Adapters, layer responsibilities | §1.1     |
| [05-composition-layer.md](02-architecture/05-composition-layer.md)                           | Composition Root, DI, Factories          | §1.1     |
| [ADR-001: Delta Lake](02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)            | Storage engine choice                    | §2.1, §3 |
| [ADR-002: Medallion](02-architecture/decisions/ADR-002-medallion-architecture.md)            | Data layering pattern                    | §1       |
| [ADR-003: Redis Locking](02-architecture/decisions/ADR-003-redis-for-distributed-locking.md) | Distributed locking                      | §6       |
| [ADR-004: Pydantic](02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md)            | Validation approach                      | -        |
| [ADR-005: Composition Layer](02-architecture/decisions/ADR-005-composition-layer-separation.md) | DI and layer separation               | §1.1     |
| [ADR-006: Logger/Metrics Ports](02-architecture/decisions/ADR-006-logger-metrics-ports.md)   | Port abstractions                        | §1.1     |
| [ADR-007: Circuit Breaker](02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) | Failure handling pattern               | §3.1.4   |
| [ADR-008: Graceful Shutdown](02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) | SIGTERM/SIGINT handling                  | §5.3     |
| [ADR-009: Paginated Fetcher](02-architecture/decisions/ADR-009-paginated-fetcher-mixin.md)   | Pagination abstraction                   | App D    |
| [ADR-010: Local-Only Deploy](02-architecture/decisions/ADR-010-local-only-deployment.md)     | File-based deployment (no Docker)        | §5.6     |
| [ADR-011: Watermark Removal](02-architecture/decisions/ADR-011-remove-watermark-mechanism.md) | Simplified checkpoint model             | §2.4     |
| [ADR-012: Storage Clear Contract](02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md) | Storage clear API, run_id injection | §2.1     |
| [ADR-013: Async Storage Cleanup](02-architecture/decisions/ADR-013-async-storage-cleanup.md) | MedallionLifecycleService pattern        | §2.1     |
| [ADR-014: Deterministic Writes](02-architecture/decisions/ADR-014-deterministic-writes.md)   | SCD2 ingestion_ts, reproducible writes   | §2.1     |
| [ADR-015: Pipeline Services Lifecycle](02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md) | Port lifecycle contracts       | §1.1     |
| [ADR-016: Error Handling Strategy](02-architecture/decisions/ADR-016-error-handling-strategy.md) | Unified error classification          | §3.1     |
| [ADR-017: Observability Architecture](02-architecture/decisions/ADR-017-observability-architecture.md) | Metrics, tracing, logging ports    | §5.1     |
| [ADR-018: Gold Strict Validation](02-architecture/decisions/ADR-018-gold-strict-validation.md) | Pandera Gold validation                | §2.7     |
| [ADR-019: Observability Port Enforcement](02-architecture/decisions/ADR-019-observability-port-enforcement.md) | REQ-OBS-001 compliance       | §5.1     |
| [ADR-020: BasePipeline Decomposition](02-architecture/decisions/ADR-020-basepipeline-decomposition.md) | God Object refactoring       | §1.1     |

### Data Management

| Topic            | Document                                                                                            | RULES.md |
|------------------|-----------------------------------------------------------------------------------------------------|----------|
| Medallion Layers | [data-flow.md](02-architecture/data-flow.md)                                                        | §2.1     |
| Schema Drift     | [01-project-rules.md](00-project_rules/01-project-rules.md)   | §2.2     |
| Data Lineage     | [system-context.md](02-architecture/system-context.md)                                              | §2.3     |
| Backfill/Replay  | [01-project-rules.md](00-project_rules/01-project-rules.md)            | §2.4     |
| Quarantine       | [01-project-rules.md](00-project_rules/01-project-rules.md) | §2.6     |
| Content Hash     | [system-context.md](02-architecture/system-context.md)                                              | §2.8     |

### Operations

| Topic             | Document                                                                                          | RULES.md |
|-------------------|---------------------------------------------------------------------------------------------------|----------|
| Error Handling    | [data-flow.md](02-architecture/data-flow.md)                                    | §3.1     |
| Circuit Breaker   | [data-flow.md](02-architecture/data-flow.md)                                  | §3.1.4   |
| Locking           | [data-flow.md](02-architecture/data-flow.md)                                | §3.3     |
| DQ Metrics        | [01-project-rules.md](00-project_rules/01-project-rules.md) | §3.4     |
| Graceful Shutdown | [data-flow.md](02-architecture/data-flow.md)                                 | §5.3     |
| DR Procedures     | [05-operations/runbooks/index.md](05-operations/runbooks/index.md)                                                      | §5.5     |
| Cleanup           | [05-cleanup-policy.md](00-project_rules/05-cleanup-policy.md)                                     | §2.1.1   |

### Development

| Topic            | Document                                                                                        | RULES.md |
|------------------|-------------------------------------------------------------------------------------------------|----------|
| Adding Providers | [add-new-source.md](03-guides/add-new-source.md)                                                | App D    |
| Adding Pipelines | [add-pipeline-existing-source.md](03-guides/add-pipeline-existing-source.md)                    | App D    |
| Pipeline Review  | [templates/pipeline-review-checklist.md](templates/pipeline-review-checklist.md)                | §4.2     |
| Testing          | [01-project-rules.md](00-project_rules/01-project-rules.md)                                     | §4.2     |
| E2E Testing      | [tests/e2e/](../tests/e2e/) + [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md) | §4.2.3 |
| Code Style       | [01-project-rules.md](00-project_rules/01-project-rules.md)                                     | §4       |

---

## Source Code Map

```
src/bioetl/
├── domain/                      # Pure logic, no I/O (§1.1)
│   ├── ports/                   # Protocol interfaces (Ports & Adapters)
│   │   ├── __init__.py          # Facade — single import point
│   │   ├── data_source.py       # DataSourcePort, FilterableDataSourcePort
│   │   ├── storage.py           # StoragePort
│   │   ├── locking.py           # LockPort
│   │   ├── checkpoint.py        # CheckpointPort
│   │   ├── quarantine.py        # QuarantinePort
│   │   ├── observability.py     # MetricsPort, TracingPort, LoggerPort
│   │   ├── validation.py        # GoldValidatorPort
│   │   └── filtering.py         # InputFilterPort
│   ├── config.py                # Domain config models
│   ├── exceptions.py            # Domain exceptions hierarchy
│   ├── transformations.py       # Pure transformation functions
│   └── types.py                 # Value objects (RunType, ErrorCode)
│
├── application/                 # Pipeline orchestration (§1.1)
│   ├── core/                    # Core pipeline infrastructure
│   │   ├── executor.py          # Batch executor
│   │   ├── pipeline_services.py # Service container
│   │   ├── shutdown.py          # Graceful shutdown handling
│   │   └── base_pipeline.py     # Abstract base pipeline
│   ├── orchestration/           # Execution coordination
│   │   └── runner.py            # PipelineRunner (Driving Adapter logic)
│   ├── pipelines/               # Concrete pipeline implementations
│   │   └── chembl_activity.py   # ChEMBL Activity pipeline
│   └── observability/           # Application-level observability
│
├── composition/                 # Composition Root (DI container)
│   ├── bootstrap.py             # Pipeline bootstrap & wiring
│   ├── registry.py              # Pipeline discovery
│   └── factories/               # Consolidated factories
│       ├── generic_factory.py   # Universal pipeline factory
│       ├── data_source_registry.py # Central source creation
│       └── storage_factory.py   # Multi-layer storage factory
│
├── infrastructure/              # I/O adapters (§1.1)
│   ├── adapters/                # External API clients
│   │   ├── http/                # HTTP client infrastructure
│   │   ├── chembl/              # ChEMBL API adapter
│   │   ├── pubchem/             # PubChem API adapter
│   │   └── uniprot/             # UniProt API adapter
│   ├── storage/                 # Data persistence
│   │   ├── bronze_writer.py     # JSONL + zstd writer
│   │   ├── delta_writer.py      # Delta Lake merge/upsert
│   │   └── gold_writer.py       # SCD Type 2 writer
│   ├── locking/                 # Distributed locking
│   │   ├── redis_lock.py        # Redis SETNX + heartbeat
│   │   └── memory_lock.py       # In-memory (dev/test)
│   ├── checkpoint/              # Checkpoint persistence
│   ├── quarantine/              # DQ failure handling
│   ├── observability/           # Metrics, logging
│   ├── schemas/                 # Pydantic config schemas
│   ├── factories/               # Infrastructure factories
│   └── config.py                # Settings (Pydantic)
│
└── interfaces/                  # External interfaces
    ├── cli.py                   # Click CLI (bioetl run/quarantine/checkpoint)
    └── orchestration/           # Pipeline orchestration adapters
        ├── signals.py           # OS signal handlers
        └── prefect/             # Prefect integration

tests/
├── unit/                        # Isolated unit tests (mock I/O)
│   ├── domain/                  # Domain logic tests
│   ├── application/             # Pipeline/transformer tests
│   └── infrastructure/          # Adapter tests
├── integration/                 # Integration tests (VCR cassettes)
│   └── adapters/                # HTTP adapter tests
├── e2e/                         # E2E tests (Local-Only arch)
│   ├── conftest.py              # E2E helpers & fixtures
│   └── test_pipeline_e2e.py     # Full pipeline cycle tests
├── architecture/                # Architecture validation tests
│   └── test_layer_imports.py    # Import matrix enforcement
└── fixtures/                    # Test fixtures
    └── vcr/                     # VCR cassettes for HTTP
```

---

## Config Files Map

```mermaid
graph TD
    subgraph configs
        direction LR
        A(pipelines) --> A1("chembl/activity.yaml")
        A --> A2("chembl/assay.yaml")
        B(schemas) --> B1("bronze/README.md")
        B --> B2("silver/README.md")
        B --> B3("gold/README.md")
        C(env) --> C1(".env.example")
    end
```

---

## Key Files

| File                                               | Purpose                   |
|----------------------------------------------------|---------------------------|
| `docs/RULES.md`                                    | Master rules document     |
| `CHANGELOG.md`                                     | Version history           |
| `configs/pipelines/{provider}/{entity}.yaml`       | Pipeline configuration    |
| `src/bioetl/domain/ports/`                         | Protocol interfaces (package) |
| `src/bioetl/composition/bootstrap.py`              | Composition root          |
| `src/bioetl/infrastructure/config.py`              | Application settings      |
| `docs/02-architecture/system-context.md`           | High-level system diagram |
| `docs/contracts/gold/{entity}.json`                | Gold data contracts       |

---

## Related Resources

- **Repository**: [SatoryKono/BioactivityDataAcquisition](https://github.com/SatoryKono/BioactivityDataAcquisition)
- **Issues**: Report bugs and feature requests
- **CI/CD**: GitHub Actions workflows

---

## Document Status

| Document                 | Last Updated | Status                       |
|--------------------------|--------------|------------------------------|
| RULES.md (docs/)         | 2025-12-27   | v5.6 (Anti-False-Claims)     |
| 01-project-rules.md      | 2025-12-18   | Redirect to RULES.md         |
| 00-rules-summary.md      | 2025-12-27   | v5.6 Synced                  |
| 00-map.md                | 2025-12-27   | Updated (ADR-020 added)      |
| CHANGELOG.md             | 2025-12-27   | v5.3.3 (Documentation)       |
| 03-guides/               | 2025-12-20   | Consolidated (6 guides)      |
| ADR-001..020             | 2025-12-27   | All 20 ADRs documented       |
| tests/e2e/               | 2025-12-23   | Local-Only E2E tests         |
| tests/architecture/      | 2025-12-26   | 213 architecture tests       |
| pyproject.toml           | 2025-12-16   | Version 5.0.0                |

---

*Last updated: 2025-12-27. Update when adding new documentation.*
