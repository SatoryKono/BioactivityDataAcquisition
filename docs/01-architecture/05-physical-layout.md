# Physical Layout
*Aligned with RULES.md v5.0*

## Обзор

Физическая структура проекта отражает слоистую архитектуру (§1.1) с чётким разделением ответственности между Domain, Application, Infrastructure и Interfaces.

---

## Таблица Маппинга Слоёв

| Логический слой | Папка | Ответственность | Правило |
|-----------------|-------|-----------------|---------|
| **Domain** | `src/bioetl/domain/` | Чистая бизнес-логика, Protocols, схемы | §1.1 |
| **Application** | `src/bioetl/application/` | Оркестрация пайплайнов, use cases | §1.1 |
| **Infrastructure** | `src/bioetl/infrastructure/` | I/O: HTTP, Storage, Locking, Logging | §1.1 |
| **Interfaces** | `src/bioetl/interfaces/` | CLI, API endpoints | §1.1 |

---

## Полная Структура Директорий

```
src/
└── bioetl/
    ├── __init__.py
    │
    ├── domain/                        # §1.1: Pure Logic (No I/O)
    │   ├── __init__.py
    │   │
    │   ├── ports.py                   # §1.1.1: Protocol interfaces
    │   ├── exceptions.py              # Domain exceptions
    │   │
    │   ├── models/                    # Pydantic models
    │   │   ├── __init__.py
    │   │   ├── base.py                # §2.4: ETLRecordBase (_run_id, _run_type)
    │   │   ├── activity.py
    │   │   ├── assay.py
    │   │   ├── molecule.py
    │   │   ├── target.py
    │   │   ├── publication.py
    │   │   ├── lineage.py             # §2.3: LineageLogEntry
    │   │   └── quarantine.py          # §2.6: QuarantineRecord
    │   │
    │   ├── schemas/                   # Pandera validation schemas
    │   │   ├── __init__.py
    │   │   ├── base.py                # Common schema patterns
    │   │   └── chembl/
    │   │       ├── __init__.py
    │   │       ├── activity.py        # ActivityTableSchema
    │   │       ├── assay.py           # AssayTableSchema
    │   │       ├── molecule.py        # MoleculeTableSchema
    │   │       ├── target.py          # TargetTableSchema
    │   │       └── publication.py     # PublicationTableSchema
    │   │
    │   ├── services/                  # Pure business logic
    │   │   ├── __init__.py
    │   │   ├── hash_service.py        # §2.8.1: Content Hash
    │   │   ├── validation_service.py  # Pandera orchestration
    │   │   └── normalization.py       # §2.8.1: Value normalization
    │   │
    │   └── rules/                     # DQ & Schema rules
    │       ├── __init__.py
    │       ├── dq_rules.py            # §3.1.2: Thresholds
    │       └── schema_drift.py        # §2.2: Drift detection
    │
    ├── application/                   # §1.1: Orchestration Layer
    │   ├── __init__.py
    │   │
    │   ├── pipelines/                 # Pipeline implementations
    │   │   ├── __init__.py
    │   │   ├── base.py                # PipelineBase
    │   │   ├── chembl/
    │   │   │   ├── __init__.py
    │   │   │   ├── base.py            # ChemblPipelineBase
    │   │   │   ├── common.py          # ChemblCommonPipeline
    │   │   │   ├── activity.py        # ChemblActivityPipeline
    │   │   │   ├── assay.py
    │   │   │   ├── molecule.py
    │   │   │   ├── target.py
    │   │   │   └── publication.py
    │   │   └── pubchem/
    │   │       ├── __init__.py
    │   │       └── compound.py
    │   │
    │   ├── services/                  # Application services
    │   │   ├── __init__.py
    │   │   ├── extraction.py          # ExtractionService
    │   │   └── schema_bootstrap.py    # SchemaBootstrapService
    │   │
    │   └── observers/                 # Cross-cutting observers
    │       ├── __init__.py
    │       ├── metrics.py             # §3.4: Prometheus DQ Metrics
    │       ├── circuit_breaker.py     # §3.1.4: Circuit Breaker
    │       └── provider_health.py     # §3.5: Provider Health
    │
    ├── infrastructure/                # §1.1: Adapters (I/O)
    │   ├── __init__.py
    │   │
    │   ├── adapters/                  # External API clients
    │   │   ├── __init__.py
    │   │   ├── chembl/
    │   │   │   ├── __init__.py
    │   │   │   ├── client.py          # ChemblClient
    │   │   │   └── health.py          # §App A: Health Check
    │   │   ├── pubchem/
    │   │   │   ├── __init__.py
    │   │   │   ├── client.py          # PubchemClient (thread pool)
    │   │   │   └── health.py
    │   │   ├── uniprot/
    │   │   │   ├── __init__.py
    │   │   │   ├── client.py
    │   │   │   └── health.py
    │   │   └── http/                  # Shared HTTP infrastructure
    │   │       ├── __init__.py
    │   │       ├── unified_client.py  # httpx async wrapper
    │   │       ├── rate_limiter.py    # §5.1: TokenBucket
    │   │       └── backpressure.py    # §5.1: Queue monitoring
    │   │
    │   ├── storage/                   # Persistence
    │   │   ├── __init__.py
    │   │   ├── delta_lake.py          # §2.1.1: delta-rs writer
    │   │   ├── bronze_writer.py       # JSONL + zstd
    │   │   ├── checkpoint.py          # §5.3.1: S3 + ETag
    │   │   └── s3_client.py           # boto3 wrapper
    │   │
    │   ├── locking/                   # §3.3: Distributed locking
    │   │   ├── __init__.py
    │   │   ├── redis_lock.py          # SETNX + Heartbeat + Fencing
    │   │   └── backfill_lock.py       # §2.4.1: Exclusive lock
    │   │
    │   ├── security/                  # §5.4: Sensitive data
    │   │   ├── __init__.py
    │   │   └── salt_manager.py        # §5.4.1: Dual-Salt rotation
    │   │
    │   ├── quarantine/                # §2.6: Quarantine operations
    │   │   ├── __init__.py
    │   │   ├── writer.py              # Write to common.quarantine
    │   │   └── ops.py                 # inspect, replay, purge
    │   │
    │   ├── config/                    # Configuration loading
    │   │   ├── __init__.py
    │   │   ├── loader.py              # YAML → Pydantic
    │   │   └── models.py              # Config Pydantic models
    │   │
    │   └── logging/                   # §3.2: Observability
    │       ├── __init__.py
    │       └── unified_logger.py      # Structured JSON (structlog)
    │
    └── interfaces/                    # External interfaces
        ├── __init__.py
        │
        ├── cli/                       # Command-line interface
        │   ├── __init__.py
        │   ├── main.py                # Entry point (Typer)
        │   └── commands/
        │       ├── __init__.py
        │       ├── run.py             # Pipeline execution
        │       ├── quarantine.py      # inspect, replay, purge
        │       ├── lock.py            # release-lock
        │       └── vacuum.py          # Delta VACUUM
        │
        └── container_factory.py       # DI container creation
```

---

## Детали по Слоям

### Domain Layer

**Расположение**: `src/bioetl/domain/`

**Зависимости**: Ничего (чистый Python + typing + pydantic + pandera)

| Компонент | Файл | Ответственность |
|-----------|------|-----------------|
| `DataSourcePort` | `ports.py` | Контракт извлечения данных |
| `SinkPort` | `ports.py` | Контракт записи данных |
| `LockPort` | `ports.py` | Контракт блокировки |
| `ETLRecordBase` | `models/base.py` | Базовые мета-поля (§2.4) |
| `HashService` | `services/hash_service.py` | Content Hash (§2.8.1) |
| `SchemaDriftDetector` | `rules/schema_drift.py` | Обнаружение дрейфа (§2.2) |

### Application Layer

**Расположение**: `src/bioetl/application/`

**Зависимости**: Domain

| Компонент | Файл | Ответственность |
|-----------|------|-----------------|
| `PipelineBase` | `pipelines/base.py` | Общий каркас стадий |
| `ChemblActivityPipeline` | `pipelines/chembl/activity.py` | Конкретный пайплайн |
| `CircuitBreaker` | `observers/circuit_breaker.py` | Защита от сбоев (§3.1.4) |
| `ProviderHealthTracker` | `observers/provider_health.py` | Мониторинг провайдера (§3.5) |

### Infrastructure Layer

**Расположение**: `src/bioetl/infrastructure/`

**Зависимости**: Domain, Application (для observers)

| Компонент | Файл | Ответственность |
|-----------|------|-----------------|
| `ChemblClient` | `adapters/chembl/client.py` | HTTP клиент ChEMBL |
| `DeltaLakeWriter` | `storage/delta_lake.py` | Delta Lake с Safety Guard |
| `RedisDistributedLock` | `locking/redis_lock.py` | Distributed lock (§3.3) |
| `SaltManager` | `security/salt_manager.py` | PII hashing (§5.4.1) |
| `QuarantineWriter` | `quarantine/writer.py` | DQ failures (§2.6) |
| `UnifiedLogger` | `logging/unified_logger.py` | Structured logging (§3.2) |

### Interfaces Layer

**Расположение**: `src/bioetl/interfaces/`

**Зависимости**: Application

| Компонент | Файл | Ответственность |
|-----------|------|-----------------|
| `main.py` | `cli/main.py` | CLI entry point |
| `run` | `cli/commands/run.py` | `bioetl run --pipeline ...` |
| `quarantine` | `cli/commands/quarantine.py` | `make quarantine-*` |
| `lock` | `cli/commands/lock.py` | `make release-lock` |

---

## Configs Structure

```
configs/
├── pipelines/                         # §App D: Pipeline YAML configs
│   ├── chembl/
│   │   ├── activity.yaml
│   │   ├── assay.yaml
│   │   ├── molecule.yaml
│   │   ├── target.yaml
│   │   └── publication.yaml
│   ├── pubchem/
│   │   └── compound.yaml
│   └── uniprot/
│       └── target.yaml
│
├── schemas/                           # Schema version configs
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
└── env/
    └── .env.example                   # §5.2: Template (no secrets)
```

---

## Tests Structure

```
tests/
├── __init__.py
├── conftest.py                        # VCR config, pytest fixtures
│
├── fixtures/
│   ├── vcr_cassettes/                 # §4.2: Recorded API responses
│   │   ├── chembl/
│   │   │   ├── activity_list.yaml
│   │   │   └── health_check.yaml
│   │   └── pubchem/
│   └── golden/                        # Golden test data
│       ├── bronze_samples/
│       ├── silver_expected/
│       └── gold_expected/
│
├── unit/                              # §4.2: Domain logic only
│   ├── domain/
│   │   ├── test_hash_service.py
│   │   ├── test_validation_service.py
│   │   ├── test_normalization.py
│   │   └── test_dq_rules.py
│   └── application/
│       ├── test_circuit_breaker.py
│       └── test_provider_health.py
│
├── integration/                       # §4.2: With VCR cassettes
│   ├── adapters/
│   │   ├── test_chembl_client.py
│   │   └── test_pubchem_client.py
│   ├── storage/
│   │   ├── test_delta_lake.py
│   │   └── test_checkpoint.py
│   └── locking/
│       └── test_redis_lock.py
│
└── contract/                          # §4.2: Monthly live API tests
    ├── test_chembl_contract.py
    └── test_pubchem_contract.py
```

---

## Docs Structure

```
docs/
├── adr/                               # Architecture Decision Records
│   ├── 001-delta-lake-choice.md
│   ├── 002-medallion-architecture.md
│   └── 003-circuit-breaker.md
│
├── contracts/                         # §7.1: Gold schema contracts
│   └── gold/
│       ├── activity_v1.0.json
│       ├── assay_v1.0.json
│       ├── molecule_v1.0.json
│       ├── target_v1.0.json
│       └── publication_v1.0.json
│
├── runbooks/                          # §App C, §5.5.1: DR procedures
│   ├── dr-bronze-corruption.md
│   ├── dr-silver-corruption.md
│   ├── dr-checkpoint-loss.md
│   ├── dr-region-failover.md
│   ├── ops-lock-timeout.md
│   ├── ops-quarantine-triage.md
│   └── alert-schema-drift.md
│
└── architecture/
    ├── 01-domain-objects.md
    ├── 02-etl-layers.md
    ├── 03-data-flow.md
    ├── 04-duplication-reduction.md
    ├── 05-physical-layout.md
    └── 06-architecture-diagrams.md
```

---

## Scripts Structure

```
scripts/
├── vacuum_delta.py                    # §2.1.1: Weekly VACUUM job
├── salt_rotate.py                     # §5.4.1: Salt rotation
├── dq_baseline_update.py              # §3.4.1: Baseline recalculation
└── init_db.sql                        # Postgres init for Docker
```

---

## Dependency Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEPENDENCY FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ Interfaces  │ ──────────────────────────────────────┐                    │
│  │    (CLI)    │                                       │                    │
│  └──────┬──────┘                                       │                    │
│         │                                              │                    │
│         ▼                                              ▼                    │
│  ┌─────────────┐         imports              ┌──────────────┐             │
│  │ Application │ ◄───────────────────────────►│Infrastructure│             │
│  │ (Pipelines) │                              │  (Adapters)  │             │
│  └──────┬──────┘                              └──────┬───────┘             │
│         │                                            │                      │
│         │         implements                         │                      │
│         ▼              ▲                             │                      │
│  ┌─────────────┐       │                             │                      │
│  │   Domain    │ ◄─────┴─────────────────────────────┘                      │
│  │  (Ports)    │      (Protocol conformance)                                │
│  └─────────────┘                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Legend:
  ─────► imports / depends on
  ◄─────  implements (Protocol conformance)
```

---

## Import Rules

### ✓ Allowed

```python
# Domain imports nothing external
from bioetl.domain.ports import DataSourcePort

# Application imports Domain
from bioetl.domain.services import HashService
from bioetl.domain.schemas.chembl import ActivityTableSchema

# Infrastructure imports Domain (for Ports)
from bioetl.domain.ports import LockPort

# Interfaces imports Application
from bioetl.application.pipelines import ChemblActivityPipeline
```

### ❌ Forbidden

```python
# Domain MUST NOT import Infrastructure
from bioetl.infrastructure.adapters import ChemblClient  # ❌

# Domain MUST NOT import Application
from bioetl.application.pipelines import PipelineBase  # ❌

# Application MUST NOT import Interfaces
from bioetl.interfaces.cli import main  # ❌
```

---

## Связи с другими документами

- **Domain Objects**: [01-domain-objects.md](01-domain-objects.md)
- **ETL Layers**: [02-etl-layers.md](02-etl-layers.md)
- **Data Flow**: [03-data-flow.md](03-data-flow.md)
- **Duplication Reduction**: [04-duplication-reduction.md](04-duplication-reduction.md)
