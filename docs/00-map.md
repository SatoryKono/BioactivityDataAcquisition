# BioETL Project Navigator

*Synced with RULES.md v5.9 | Last updated: 2026-01-05*

> **Documentation Audit Completed:** 2026-01-05
> - Consolidated duplicate `audit/` and `audits/` directories → `audits/`
> - Consolidated duplicate `operations/` and `05-operations/` directories → `05-operations/`
> - Fixed 30+ broken relative links
> - Updated version references to v5.9
> - 34 Mermaid diagrams maintained in `02-architecture/diagrams/`
> - Added `02-architecture/00-overview.md` navigation document

## Quick Links

| Need to...              | Go to                                                                  |
|-------------------------|------------------------------------------------------------------------|
| Understand the rules    | [RULES.md](RULES.md)                 |
| Look up terminology     | [glossary.md](glossary.md)           |
| Create a new pipeline   | [00-project_rules/04-extending-bioetl.md](00-project_rules/04-extending-bioetl.md)      |
| Review a pipeline       | [templates/pipeline-review-checklist.md](templates/pipeline-review-checklist.md) |
| Handle a prod error     | [05-operations/runbooks/index.md](05-operations/runbooks/index.md)                           |
| Understand architecture | [02-architecture/00-overview.md](02-architecture/00-overview.md)                  |
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
├── index.md                     # Welcome page
├── glossary.md                  # Ubiquitous Language terminology
├── RULES.md                     # Canonical rules document (v5.9)
├── REQUIREMENTS.md              # 127 testable requirements
├── CHANGELOG.md                 # Version history
├── refactoring-plan.md          # Current refactoring roadmap
│
├── 00-project_rules/            # Project governance
│   ├── 00-rules-summary.md      # TL;DR of RULES.md
│   ├── 02-user-rules.md         # Guidelines for contributors
│   ├── 03-file-policy.md        # File/directory structure
│   ├── 04-extending-bioetl.md   # How to add providers/pipelines
│   ├── 05-cleanup-policy.md     # Cleanup and retention
│   ├── 06-rules-mapping.md      # RULES.md to docs mapping
│   └── 07-consistency-check.md  # Consistency verification guide
│
├── 02-architecture/             # System architecture
│   ├── 00-overview.md           # Architecture overview & navigation
│   ├── 01-domain-layer.md       # Domain layer architecture
│   ├── 02-application-layer.md  # Application layer architecture
│   ├── 03-infrastructure-layer.md # Infrastructure layer architecture
│   ├── 04-interfaces-layer.md   # Interfaces layer architecture
│   ├── 05-composition-layer.md  # Composition layer (DI) architecture
│   ├── system-context.md        # C4 System Context Diagram
│   ├── container-diagram.md     # C4 Container Diagram
│   ├── data-flow.md             # High-level Medallion data flow
│   ├── data-layers.md           # Bronze/Silver/Gold layer details
│   ├── observability-layers.md  # Observability architecture
│   ├── diagrams.md              # Mermaid diagrams collection
│   ├── decisions/               # ADR-001..022 (22 records)
│   └── diagrams/                # 34 Mermaid diagram files + render_diagrams.py
│
├── 03-guides/                   # How-to guides (10 guides)
│   ├── quick-start.md           # Quick start guide
│   ├── getting-started.md       # Getting started
│   ├── running-pipelines.md     # Running pipelines
│   ├── testing.md               # Testing guide
│   ├── local-storage-layout.md  # Storage layout explanation
│   ├── pipeline-lifecycle.md    # Pipeline lifecycle
│   ├── registry-pattern.md      # Registry pattern guide
│   ├── troubleshooting.md       # Troubleshooting
│   ├── add-new-source.md        # Adding new data source
│   └── add-pipeline-existing-source.md
│
├── 03-data-contracts/           # Data contracts
│   └── gold-schemas.md          # Gold layer schema documentation
│
├── 04-reference/                # Reference documentation
│   ├── api/                     # API reference by layer
│   ├── cli.md                   # CLI reference
│   └── pipelines/               # Pipeline-specific reference
│
├── 05-operations/               # Operational runbooks
│   ├── runbooks/                # 16 incident response playbooks
│   └── performance-baselines.md # Performance metrics
│
├── audits/                      # Architecture audits (consolidated)
│   ├── audit-2025-12-31-comprehensive.md  # Latest comprehensive audit
│   ├── architecture-audit-2025-12-31.md   # Architecture audit
│   ├── application-layer-audit.md         # Application layer
│   ├── infrastructure-layer-audit.md      # Infrastructure layer
│   ├── interfaces-layer-audit-2025-12-30.md # Interfaces layer
│   ├── false_positives.md                 # Documented false positives
│   └── validation-matrix-2025-12-31.md    # Validation matrix
│
├── archived/                    # Historical documents
│   ├── refactoring-plan-bronze-validation.md
│   ├── consolidated-refactoring-analysis.md
│   └── (7 more archived plans/issues)
│
├── domain/schemas/              # Schema documentation
│   └── chembl/                  # ChEMBL entity schemas (4 files)
│
├── providers/                   # Provider-specific documentation
│   ├── chembl/                  # ChEMBL (6 entities)
│   ├── pubchem/                 # PubChem (1 entity)
│   ├── uniprot/                 # UniProt (1 entity)
│   └── pubmed/                  # PubMed (1 entity)
│
├── contracts/gold/              # Gold layer JSON schemas
│
├── templates/                   # Document & code templates
│
└── __-prompts/                  # Claude prompts (internal)
```

---

## By Topic

### Getting Started

1. [RULES.md](RULES.md) - Project rules (start here)
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
| [ADR-003: In-Memory Locking](02-architecture/decisions/ADR-003-in-memory-locking-strategy.md) | MemoryLock strategy                      | §6       |
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
| Schema Drift     | [RULES.md](RULES.md#22-обработка-дрейфа-схемы)   | §2.2     |
| Data Lineage     | [system-context.md](02-architecture/system-context.md)                                              | §2.3     |
| Backfill/Replay  | [RULES.md](RULES.md#24-стратегия-backfill-и-replay)            | §2.4     |
| Quarantine       | [RULES.md](RULES.md#26-dead-letter-queue--quarantine) | §2.6     |
| Content Hash     | [system-context.md](02-architecture/system-context.md)                                              | §2.8     |

### Schema Documentation

| Provider | Entity | Schema Document | RULES.md |
|----------|--------|-----------------|----------|
| ChEMBL | Activity | [activity-schema.md](domain/schemas/chembl/activity-schema.md) | §2.8 |
| ChEMBL | Molecule | [molecule-schema.md](domain/schemas/chembl/molecule-schema.md) | §2.8 |
| ChEMBL | Target | [target-schema.md](domain/schemas/chembl/target-schema.md) | §2.8 |
| ChEMBL | Assay | [assay-schema.md](domain/schemas/chembl/assay-schema.md) | §2.8 |

### Operations

| Topic             | Document                                                                                          | RULES.md |
|-------------------|---------------------------------------------------------------------------------------------------|----------|
| Error Handling    | [ADR-016](02-architecture/decisions/ADR-016-error-handling-strategy.md)         | §3.1     |
| Circuit Breaker   | [ADR-007](02-architecture/decisions/ADR-007-circuit-breaker-implementation.md)  | §3.1.4   |
| Locking           | [ADR-003](02-architecture/decisions/ADR-003-in-memory-locking-strategy.md)      | §3.3     |
| DQ Metrics        | [RULES.md](RULES.md#34-data-quality-метрики)                                    | §3.4     |
| Graceful Shutdown | [ADR-008](02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)      | §5.3     |
| DR Procedures     | [runbooks/index.md](05-operations/runbooks/index.md)                            | §5.5     |
| Cleanup           | [05-cleanup-policy.md](00-project_rules/05-cleanup-policy.md)                   | §2.1.1   |

### Development

| Topic            | Document                                                                                        | RULES.md |
|------------------|-------------------------------------------------------------------------------------------------|----------|
| Adding Providers | [add-new-source.md](03-guides/add-new-source.md)                                                | App D    |
| Adding Pipelines | [add-pipeline-existing-source.md](03-guides/add-pipeline-existing-source.md)                    | App D    |
| Pipeline Review  | [pipeline-review-checklist.md](templates/pipeline-review-checklist.md)                          | §4.2     |
| Testing          | [testing.md](03-guides/testing.md)                                                              | §4.2     |
| E2E Testing      | [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md)                           | §4.2.3   |
| Code Style       | [02-user-rules.md](00-project_rules/02-user-rules.md)                                           | §4       |

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
        └── signals.py           # OS signal handlers

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
| `docs/glossary.md`                                 | Ubiquitous Language terminology |
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
| RULES.md                 | 2026-01-01   | v5.9 (TTL/Heartbeat Sync)    |
| refactoring-plan.md      | 2025-12-31   | Active refactoring roadmap   |
| REQUIREMENTS.md          | 2025-12-27   | v1.2 (127 requirements)      |
| glossary.md              | 2025-12-29   | v1.0 (Ubiquitous Language)   |
| 00-map.md                | 2026-01-04   | v6.2 Consolidated operations |
| 00-rules-summary.md      | 2026-01-01   | v5.9 Synced                  |
| 03-guides/               | 2025-12-31   | Consolidated (10 guides)     |
| ADR-001..022             | 2025-12-31   | All 22 ADRs documented       |
| 05-operations/runbooks/  | 2026-01-04   | 16 active runbooks           |
| domain/schemas/          | 2025-12-28   | ChEMBL schemas (4 entities)  |
| audits/                  | 2026-01-04   | Consolidated (27 files)      |
| 02-architecture/diagrams/| 2025-12-31   | 34 Mermaid diagrams          |

---

*Last updated: 2026-01-04. Documentation audit completed.*
