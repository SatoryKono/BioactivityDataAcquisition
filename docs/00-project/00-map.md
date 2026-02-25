# BioETL Project Navigator

*Synced with RULES.md v5.22 | Last updated: 2026-02-25*

> **Documentation Update:** 2026-02-25
> - Codebase metrics updated: 1,120 Python files (534 src + 586 tests), ~116,120 src LOC
> - ADR count: 39 ADRs (ADR-001 through ADR-039)
> - Pipeline configs: 26 configurations (21 single-source + 5 composite)
> - YAML configs total: 121 (26 pipelines + 35 DQ + 34 filters + 26 schemas)
> - Documentation files: 366 markdown files
> - Adapter listing completed (all 7 providers)
> - Diagrams: 50+ Mermaid source files

## Quick Links

| Need to...              | Go to                                                                  |
|-------------------------|------------------------------------------------------------------------|
| Understand the rules    | [RULES.md](RULES.md)                 |
| Look up terminology     | [glossary.md](glossary.md)           |
| Create a new pipeline   | [governance/04-extending-bioetl.md](governance/04-extending-bioetl.md)      |
| Review a pipeline       | [pipeline-review-checklist.md](../04-reference/templates/pipeline-review-checklist.md) |
| Handle a prod error     | [runbooks/index.md](../05-operations/runbooks/index.md)                           |
| Understand architecture | [00-overview.md](../02-architecture/00-overview.md)                  |
| Check data contracts    | [chembl_activity_v1.0.json](../04-reference/contracts/gold/chembl_activity_v1.0.json)          |

---

## Language Policy

| Category | Language | Examples |
|----------|----------|----------|
| **Public-facing** | English | README.md, CONTRIBUTING.md, CHANGELOG.md |
| **User guides** | English | docs/03-guides/*, docs/04-reference/* |
| **Internal governance** | Russian | RULES.md, AGENT.md, docs/00-project/governance/* |
| **Architecture docs** | Russian | docs/02-architecture/* |
| **Code comments** | Russian | Docstrings, inline comments |

---

## Documentation Structure

```
docs/
├── 00-project/                  # Project rules & governance
│   ├── 00-map.md                # This file (Project Navigator)
│   ├── index.md                 # Welcome page
│   ├── RULES.md                 # Canonical rules document (v5.21)
│   ├── glossary.md              # Ubiquitous Language terminology
│   ├── TOOLS.md                 # Tools & Setup
│   ├── rules-summary.md         # TL;DR of RULES.md
│   └── governance/              # Project governance policies
│       ├── 02-naming-policy.md  # Entity naming conventions
│       ├── 03-file-policy.md
│       ├── 04-extending-bioetl.md
│       └── 05-github-policy.md  # CI/CD, branch protection, reviews
│
├── 01-requirements/             # Requirements
│   └── REQUIREMENTS.md          # 156 testable requirements
│
├── 02-architecture/             # Architecture & Decisions
│   ├── 00-overview.md           # Architecture overview
│   ├── decisions/               # ADRs (ADR-001..039)
│   ├── diagrams/                # System diagrams
│   │   └── mermaid/             # Mermaid source files
│   └── ... (Layer docs: 01-domain, 02-application, etc.)
│
├── 03-guides/                   # Guides & Manuals
│   ├── development/             # Developer guides (config schema, etc.)
│   ├── quick-ref/               # Quick reference cheat sheets
│   └── ... (User guides: getting-started, testing, etc.)
│
├── 04-reference/                # Reference Documentation
│   ├── api/                     # API Reference
│   ├── cli.md                   # CLI Reference
│   ├── providers/               # Provider documentation (ChEMBL, PubMed, etc.)
│   ├── pipelines/               # Pipeline specifications
│   ├── contracts/               # Data Contracts (Gold layer schemas)
│   ├── schemas/                 # Auxiliary schemas & field maps
│   └── templates/               # Code & doc templates
│
├── 05-operations/               # Operations & Runbooks
│   ├── runbooks/                # Incident response playbooks
│   ├── verification/            # Data verification reports
│   └── ... (Ops guides: vacuum, performance)
│
└── 99-archive/                  # Archived / Deprecated
    ├── reports/                 # Old project reports
    └── ...
```

---

## By Topic

### Getting Started

1. [RULES.md](RULES.md) - Project rules (start here)
2. [rules-summary.md](rules-summary.md) - Quick reference
3. [04-extending-bioetl.md](governance/04-extending-bioetl.md) - Adding providers/pipelines

### Architecture

| Document                                                                                     | Covers                                   | RULES.md |
|----------------------------------------------------------------------------------------------|------------------------------------------|----------|
| [system-context.md](../02-architecture/system-context.md)                                       | Entity models, IDs, relationships        | §2.8     |
| [container-diagram.md](../02-architecture/container-diagram.md)                               | C4 Container, Docker services            | §5.6     |
| [data-flow.md](../02-architecture/data-flow.md)                                                 | Ports & Adapters, layer responsibilities | §1.1     |
| [05-composition-layer.md](../02-architecture/05-composition-layer.md)                           | Composition Root, DI, Factories          | §1.1     |
| [ADR-001: Delta Lake](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)            | Storage engine choice                    | §2.1, §3 |
| [ADR-002: Medallion](../02-architecture/decisions/ADR-002-medallion-architecture.md)            | Data layering pattern                    | §1       |
| [ADR-003: In-Memory Locking](../02-architecture/decisions/ADR-003-in-memory-locking-strategy.md) | MemoryLock strategy                      | §6       |
| [ADR-004: Pydantic](../02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md)            | Validation approach                      | -        |
| [ADR-005: Composition Layer](../02-architecture/decisions/ADR-005-composition-layer-separation.md) | DI and layer separation               | §1.1     |
| [ADR-006: Logger/Metrics Ports](../02-architecture/decisions/ADR-006-logger-metrics-ports.md)   | Port abstractions                        | §1.1     |
| [ADR-007: Circuit Breaker](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) | Failure handling pattern               | §3.1.4   |
| [ADR-008: Graceful Shutdown](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) | SIGTERM/SIGINT handling                  | §5.3     |
| [ADR-009: Paginated Fetcher](../02-architecture/decisions/ADR-009-paginated-fetcher-mixin.md)   | Pagination abstraction                   | App D    |
| [ADR-010: Local-Only Deploy](../02-architecture/decisions/ADR-010-local-only-deployment.md)     | File-based deployment (no Docker)        | §5.6     |
| [ADR-011: Watermark Removal](../02-architecture/decisions/ADR-011-remove-watermark-mechanism.md) | Simplified checkpoint model             | §2.4     |
| [ADR-012: Storage Clear Contract](../02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md) | Storage clear API, run-id injection | §2.1     |
| [ADR-013: Async Storage Cleanup](../02-architecture/decisions/ADR-013-async-storage-cleanup.md) | MedallionLifecycleService pattern        | §2.1     |
| [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)   | SCD2 ingestion-ts, reproducible writes   | §2.1     |
| [ADR-015: Pipeline Services Lifecycle](../02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md) | Port lifecycle contracts       | §1.1     |
| [ADR-016: Error Handling Strategy](../02-architecture/decisions/ADR-016-error-handling-strategy.md) | Unified error classification          | §3.1     |
| [ADR-017: Observability Architecture](../02-architecture/decisions/ADR-017-observability-architecture.md) | Metrics, tracing, logging ports    | §5.1     |
| [ADR-018: Gold Strict Validation](../02-architecture/decisions/ADR-018-gold-strict-validation.md) | Pandera Gold validation                | §2.7     |
| [ADR-019: Observability Port Enforcement](../02-architecture/decisions/ADR-019-observability-port-enforcement.md) | REQ-OBS-001 compliance       | §5.1     |
| [ADR-020: BasePipeline Decomposition](../02-architecture/decisions/ADR-020-basepipeline-decomposition.md) | God Object refactoring       | §1.1     |
| [ADR-021: DDD Aggregates](../02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md) | DDD aggregates adoption       | -        |
| [ADR-022: Tracing NoOp](../02-architecture/decisions/ADR-022-tracing-noop.md) | NoOp for tracing              | -        |
| [ADR-023: Entity Type Patterns](../02-architecture/decisions/ADR-023-entity-type-patterns.md) | Entity type patterns          | -        |
| [ADR-024: Entity Naming Unification](../02-architecture/decisions/ADR-024-entity-naming-unification.md) | Entity naming unification     | -        |
| [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md) | Pipeline config unification   | -        |
| [ADR-026: Composite Pipeline Pattern](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) | Composite pipeline pattern    | -        |
| [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md) | Hierarchical DQ configuration | §3.1.2   |
| [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md) | Hierarchical filter configuration | App D   |
| [ADR-029: Output Metadata Unification](../02-architecture/decisions/ADR-029-output-metadata-unification.md) | Unified output metadata contracts | §2.4    |
| [ADR-030: Publication Pagination Strategy](../02-architecture/decisions/ADR-030-publication-pagination-strategy.md) | Publication pagination strategy | -       |
| [ADR-031: Loading Strategy Formalization](../02-architecture/decisions/ADR-031-loading-strategy-formalization.md) | Loading strategy formalization | -       |
| [ADR-032: Unified HTTP Client](../02-architecture/decisions/ADR-032-unified-http-client.md) | Unified HTTP client pattern | App A   |
| [ADR-033: Publication Validation Strategy](../02-architecture/decisions/ADR-033-publication-validation-strategy.md) | Five-level publication validation | §3.4 |
| [ADR-034: Schema↔Domain Pairs](../02-architecture/decisions/ADR-034-schema-domain-pairs.md) | Schema↔Domain configuration pairs | §2.8 |
| [ADR-035: JSON Field Typing Policy](../02-architecture/decisions/ADR-035-json-field-typing-policy.md) | JSON field typing (Silver↔Gold) | §2.8 |
| [ADR-036: Gold Contract Versioning](../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) | Gold contract versioning policy | §2.7 |
| [ADR-037: Canonical Schema Generation](../02-architecture/decisions/ADR-037-canonical-schema-generation.md) | Canonical schema source and generation | §2.8 |
| [ADR-038: Enum Externalization](../02-architecture/decisions/ADR-038-enum-externalization.md) | ChEMBL enum values externalization | App D |
| [ADR-039: Unified Entity Config](../02-architecture/decisions/ADR-039-unified-entity-config-format.md) | Unified entity configuration format | App D |

### Data Management

| Topic            | Document                                                                                            | RULES.md |
|------------------|-----------------------------------------------------------------------------------------------------|----------|
| Medallion Layers | [data-flow.md](../02-architecture/data-flow.md)                                                        | §2.1     |
| Schema Drift     | [RULES.md](RULES.md#22-политика-дрейфа-схемы-schema-drift)   | §2.2     |
| Data Lineage     | [system-context.md](../02-architecture/system-context.md)                                              | §2.3     |
| Backfill/Replay  | [RULES.md](RULES.md#24-политика-backfill--replay)            | §2.4     |
| Quarantine       | [RULES.md](RULES.md#26-политика-null-и-пропущенных-значений) | §2.6     |
| Content Hash     | [system-context.md](../02-architecture/system-context.md)                                              | §2.8     |

### Schema Documentation

| Provider | Entity | Schema Document | RULES.md |
|----------|--------|-----------------|----------|
| ChEMBL | Activity | [activity-schema.md](../04-reference/schemas/domain/chembl/activity-schema.md) | §2.8 |
| ChEMBL | Molecule | [molecule-schema.md](../04-reference/schemas/domain/chembl/molecule-schema.md) | §2.8 |
| ChEMBL | Target | [target-schema.md](../04-reference/schemas/domain/chembl/target-schema.md) | §2.8 |
| ChEMBL | Assay | [assay-schema.md](../04-reference/schemas/domain/chembl/assay-schema.md) | §2.8 |

### Operations

| Topic             | Document                                                                                          | RULES.md |
|-------------------|---------------------------------------------------------------------------------------------------|----------|
| Error Handling    | [ADR-016](../02-architecture/decisions/ADR-016-error-handling-strategy.md)         | §3.1     |
| Circuit Breaker   | [ADR-007](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md)  | §3.1.4   |
| Locking           | [ADR-003](../02-architecture/decisions/ADR-003-in-memory-locking-strategy.md)      | §3.3     |
| DQ Metrics        | [RULES.md](RULES.md#34-data-quality)                                    | §3.4     |
| Graceful Shutdown | [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)      | §5.3     |
| DR Procedures     | [runbooks/index.md](../05-operations/runbooks/index.md)                            | §5.5     |
| Cleanup           | [cleanup-policy.md](../03-guides/cleanup-policy.md)                                | §2.1.1   |

### Development

| Topic            | Document                                                                                        | RULES.md |
|------------------|-------------------------------------------------------------------------------------------------|----------|
| Adding Providers | [add-new-source.md](../03-guides/add-new-source.md)                                                | App D    |
| Adding Pipelines | [add-pipeline-existing-source.md](../03-guides/add-pipeline-existing-source.md)                    | App D    |
| Pipeline Review  | [pipeline-review-checklist.md](../04-reference/templates/pipeline-review-checklist.md)                          | §4.2     |
| Testing          | [testing.md](../03-guides/testing.md)                                                              | §4.2     |
| E2E Testing      | [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)                           | §4.2.3   |
| Date Handling    | [date-handling.md](../03-guides/date-handling.md)                                                  | §2.4     |
| Code Style       | [RULES.md §4](RULES.md#4-качество-кода-и-тестирование)                                          | §4       |

---

## Source Code Map

```
src/bioetl/
├── domain/                      # Pure logic, no I/O (§1.1)
│   ├── ports/                   # Protocol interfaces (Ports & Adapters)
│   │   ├── --init--.py          # Facade — single import point
│   │   ├── data-source.py       # DataSourcePort, FilterableDataSourcePort
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
│   │   ├── base.py              # Base pipeline primitives
│   │   ├── base-transformer.py  # Base transformer contracts
│   │   ├── batch-executor.py    # Batch executor
│   │   ├── pipeline-services.py # Service container
│   │   ├── runner.py            # PipelineRunner (Driving Adapter logic)
│   │   └── shutdown.py          # Graceful shutdown handling
│   ├── composite/               # Composite pipeline orchestration
│   ├── pipelines/               # Concrete pipeline implementations
│   │   ├── common/              # Shared pipeline helpers
│   │   ├── chembl/              # Provider namespace
│   │   │   ├── activity.py      # ChEMBL Activity pipeline
│   │   │   ├── assay.py         # ChEMBL Assay pipeline
│   │   │   └── molecule.py      # ChEMBL Molecule pipeline
│   │   ├── pubchem/             # Provider namespace
│   │   │   └── compound.py      # PubChem Compound pipeline
│   │   ├── pubmed/              # Provider namespace
│   │   │   └── publication.py   # PubMed Publication pipeline
│   │   ├── uniprot/             # Provider namespace
│   │   │   └── protein.py       # UniProt Protein pipeline
│   │   ├── crossref/            # Provider namespace
│   │   │   └── transformer.py   # CrossRef transformer
│   │   ├── openalex/            # Provider namespace
│   │   │   └── transformer.py   # OpenAlex transformer
│   │   ├── semanticscholar/     # Provider namespace
│   │   │   └── transformer.py   # SemanticScholar transformer
│   │   └── generic.py           # Generic pipeline helpers
│   ├── services/                # Application services
│   └── observability/           # Application-level observability
│
├── composition/                 # Composition Root (DI container)
│   ├── bootstrap/               # Bootstrap helpers
│   ├── bootstrap-contexts.py    # Bootstrap contexts
│   ├── bootstrap-logger.py      # Bootstrap logging setup
│   ├── builders.py              # Composition builders
│   ├── entrypoints.py           # CLI/runner entrypoints
│   ├── observability.py         # Observability wiring
│   ├── registry.py              # Pipeline discovery
│   ├── providers/               # Provider registration
│   ├── services/                # Composition services
│   └── factories/               # Consolidated factories
│       ├── pipeline_factory.py  # Pipeline factory
│       ├── runner_factory.py    # Runner factory
│       └── storage_factory.py   # Multi-layer storage factory
│
├── infrastructure/              # I/O adapters (§1.1)
│   ├── adapters/                # External API clients
│   │   ├── http/                # HTTP client infrastructure
│   │   ├── chembl/              # ChEMBL API adapter
│   │   ├── crossref/            # CrossRef API adapter
│   │   ├── openalex/            # OpenAlex API adapter
│   │   ├── pubchem/             # PubChem API adapter
│   │   ├── pubmed/              # PubMed API adapter
│   │   ├── semanticscholar/     # Semantic Scholar API adapter
│   │   └── uniprot/             # UniProt API adapter
│   ├── storage/                 # Data persistence
│   │   ├── bronze-writer.py     # JSONL + zstd writer
│   │   ├── base-delta-writer.py  # Delta Lake merge/upsert
│   │   ├── silver-writer.py     # Silver layer writer
│   │   └── gold-writer.py       # SCD Type 2 writer
│   ├── locking/                 # Distributed locking
│   │   └── memory-lock.py       # In-memory (local-only)
│   ├── checkpoint/              # Checkpoint persistence
│   ├── quarantine/              # DQ failure handling
│   ├── observability/           # Metrics, logging
│   ├── schemas/                 # Pydantic config schemas
│   ├── factories/               # Infrastructure factories
│   └── config.py                # Settings (Pydantic)
│
└── interfaces/                  # External interfaces
    ├── cli/                     # CLI package (bioetl run/quarantine/checkpoint)
    │   ├── --init--.py          # CLI package entry
    │   ├── --main--.py          # CLI module entrypoint
    │   ├── exit-codes.py        # CLI exit codes
    │   ├── formatters.py        # CLI output formatting
    │   ├── main.py              # Click command group
    │   └── commands/            # CLI subcommands
    ├── http/                    # HTTP interfaces (health server)
    │   ├── health-server.py     # Health server
    │   └── types.py             # HTTP types
    ├── orchestration/           # Orchestration helpers
    └── observability.py         # Interface observability wiring

tests/
├── unit/                        # Isolated unit tests (mock I/O)
│   ├── domain/                  # Domain logic tests
│   ├── application/             # Pipeline/transformer tests
│   └── infrastructure/          # Adapter tests
├── integration/                 # Integration tests (VCR cassettes)
│   └── adapters/                # HTTP adapter tests
├── e2e/                         # E2E tests (Local-Only arch)
│   ├── conftest.py              # E2E helpers & fixtures
│   └── test-pipeline_e2e.py     # Full pipeline cycle tests
├── architecture/                # Architecture validation tests
│   └── test-layer-imports.py    # Import matrix enforcement
└── fixtures/                    # Test fixtures
    └── vcr/                     # VCR cassettes for HTTP
```

---

## Config Files Map

```mermaid
graph TD
    subgraph configs
        direction LR
        A(entities) --> A1("chembl/activity.yaml")
        A --> A2("pubmed/publication.yaml")
        B(providers) --> B1("chembl.yaml")
        B --> B2("openalex.yaml")
        C(base) --> C1("pipeline.yaml")
        C --> C2("quality.yaml")
        D(composites) --> D1("publication.yaml")
    end
```

---

## Key Files

| File                                               | Purpose                   |
|----------------------------------------------------|---------------------------|
| `docs/00-project/RULES.md`                         | Master rules document     |
| `docs/00-project/glossary.md`                      | Ubiquitous Language terminology |
| `CHANGELOG.md`                                     | Version history           |
| `configs/entities/{provider}/{entity}.yaml`       | Pipeline configuration    |
| `src/bioetl/domain/ports/`                         | Protocol interfaces (package) |
| `src/bioetl/composition/bootstrap-contexts.py`     | Composition root          |
| `src/bioetl/infrastructure/config.py`              | Application settings      |
| `docs/02-architecture/system-context.md`           | High-level system diagram |
| `docs/04-reference/contracts/gold/{entity}.json`   | Gold data contracts       |

---

### CI/CD & GitHub

| Topic | Document | RULES.md |
|-------|----------|----------|
| GitHub Policy | [05-github-policy.md](governance/05-github-policy.md) | §4, §5 |
| Contributing | [CONTRIBUTING.md](https://github.com/SatoryKono/BioactivityDataAcquisition2/blob/main/.github/CONTRIBUTING.md) | — |
| Security | [SECURITY.md](https://github.com/SatoryKono/BioactivityDataAcquisition2/blob/main/.github/SECURITY.md) | §5.4 |

## Related Resources

- **Repository**: [SatoryKono/BioactivityDataAcquisition2](https://github.com/SatoryKono/BioactivityDataAcquisition2)
- **Issues**: Report bugs and feature requests
- **CI/CD**: GitHub Actions workflows ([GitHub Policy](governance/05-github-policy.md))

---

## Document Status

| Document                 | Last Updated | Status                       |
|--------------------------|--------------|------------------------------|
| RULES.md                 | 2026-02-24   | v5.22 (Latest)               |
| REQUIREMENTS.md          | 2026-02-21   | v1.5 (Local-Only sync)       |
| glossary.md              | 2026-02-06   | v2.5 (Ubiquitous Language)   |
| 00-map.md                | 2026-02-25   | v7.4 ADR-033..039 added      |
| rules-summary.md         | 2026-02-24   | v5.22 Synced                 |
| TOOLS.md                 | 2026-02-24   | v2.2 Synced with RULES v5.22 |
| 03-guides/               | 2026-01-20   | Consolidated (16 guides)     |
| 03-development/          | 2026-01-26   | Config schema guidelines     |
| ADR-001..039             | 2026-02-24   | All 39 ADRs documented       |
| 05-operations/runbooks/  | 2026-01-04   | 16 active runbooks           |
| domain/schemas/          | 2025-12-28   | ChEMBL schemas (4 entities)  |
| audits/                  | 2026-02-17   | Consolidated (audit/ merged) |
| 02-architecture/diagrams/| 2025-12-31   | 50+ Mermaid diagrams         |

---

*Last updated: 2026-02-25. ADR-033..039 added, version sync v5.22.*
