______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Architecture Diagrams - BioETL

Комплексная система архитектурных диаграмм для понимания структуры, потоков данных и компонентов проекта BioETL.

______________________________________________________________________

## Содержание

1. [Обзорные Архитектурные Диаграммы](#1-%D0%BE%D0%B1%D0%B7%D0%BE%D1%80%D0%BD%D1%8B%D0%B5-%D0%B0%D1%80%D1%85%D0%B8%D1%82%D0%B5%D0%BA%D1%82%D1%83%D1%80%D0%BD%D1%8B%D0%B5-%D0%B4%D0%B8%D0%B0%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D1%8B)
1. [Потоки Данных](#2-%D0%BF%D0%BE%D1%82%D0%BE%D0%BA%D0%B8-%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85)
1. [Компонентные Диаграммы](#3-%D0%BA%D0%BE%D0%BC%D0%BF%D0%BE%D0%BD%D0%B5%D0%BD%D1%82%D0%BD%D1%8B%D0%B5-%D0%B4%D0%B8%D0%B0%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D1%8B)
1. [Паттерны и Механизмы](#4-%D0%BF%D0%B0%D1%82%D1%82%D0%B5%D1%80%D0%BD%D1%8B-%D0%B8-%D0%BC%D0%B5%D1%85%D0%B0%D0%BD%D0%B8%D0%B7%D0%BC%D1%8B)
1. [Конфигурация и Схемы](#5-%D0%BA%D0%BE%D0%BD%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%B0%D1%86%D0%B8%D1%8F-%D0%B8-%D1%81%D1%85%D0%B5%D0%BC%D1%8B)

______________________________________________________________________

## 1. Обзорные Архитектурные Диаграммы

### 1.1 Five Layer Architecture

[Five Layer Architecture](../foundation/01-high-level.mmd)

**Приоритет:** 9.69 | **Тип:** Component Diagram

**Описание:**

Фундаментальная архитектура проекта BioETL с пятью чёткими слоями:

- **Domain Layer** - Чистая бизнес-логика без I/O:

  - representative DDD aggregates (PipelineRun, Batch, QuarantineEntry)
  - port families and protocol interfaces
  - canonical domain entity families (ChemblActivity, UniProtProtein и др.)
  - value-object families
  - pure domain service families

- **Application Layer** - Use Cases и оркестрация:

  - runner, batch-execution, lifecycle, preflight и postrun families в `application/core`
  - provider-specific pipelines + `GenericPipeline` facades в `application/pipelines`
  - application services, observability helpers и composite orchestration

- **Composition Layer** - Dependency Injection:

  - runtime/bootstrap entrypoints (`bootstrap_pipeline_runner()`, `bootstrap_composite_runner()`, CLI bootstrap helpers)
  - provider loading lifecycle, registry helpers и factory families
  - public composition seams (`entrypoints`, `execution_api`, `control_plane_api`, `health_api`, `maintenance_api`, `resources_api`)

- **Infrastructure Layer** - Адаптеры:

  - storage writers/readers, metadata/storage support packages
  - provider adapters and HTTP infrastructure
  - config loading, normalization and persistence support packages

- **Interfaces Layer** - Entry Points:

  - CLI command families for run, run-all, inspect, admin and maintenance flows

**Ключевые правила:**

- ❌ Domain НЕ импортирует Application/Infrastructure
- ✅ Infrastructure реализует Domain Ports
- ✅ Composition собирает зависимости

**Файл:** [`docs/02-architecture/diagrams/foundation/01-high-level.mmd`](../foundation/01-high-level.mmd)

______________________________________________________________________

### 1.2 Hexagonal Architecture Overview

[Hexagonal Architecture](../foundation/26-hexagonal-ports-adapters.mmd)

**Приоритет:** 9.50 | **Тип:** C4 Context Diagram

**Описание:**

Ports & Adapters паттерн - ключевой архитектурный принцип проекта.

**Inbound Adapters:**

- CLI Interface (Click commands)

**Outbound Adapters:**

- 7 Provider Adapters (ChEMBL, PubChem, UniProt, CrossRef, OpenAlex, PubMed, SemanticScholar)
- Storage Adapters (BronzeWriter, SilverWriter, GoldWriter)
- Observability Adapters (StructlogLogger, PrometheusMetrics, OTELTracer)
- Coordination Adapters (MemoryLock, LocalCheckpointAdapter, UnifiedQuarantineAdapter)

**Domain Core:**

- DDD Aggregates
- Entities
- Value Objects
- Domain Services

**Port families and protocol surfaces:**

- DataSourcePort, BronzeStoragePort, SilverStoragePort, GoldStoragePort, MergedStoragePort
- LockPort, CheckpointPort, QuarantinePort
- TracingPort, MetricsPort, LoggerPort
- И другие...

**Файл:** [`docs/02-architecture/diagrams/foundation/26-hexagonal-ports-adapters.mmd`](../foundation/26-hexagonal-ports-adapters.mmd)

______________________________________________________________________

### 1.3 Layer Dependency Matrix

[Layer Dependency Matrix](../foundation/27-import-matrix-enforcement.mmd)

**Приоритет:** 9.44 | **Тип:** Matrix Diagram

**Описание:**

Матрица разрешённых импортов между слоями. Enforcement через:

- `tests/architecture/test_layer_dependencies.py`
- `import-linter` configuration
- CI pipeline (`make test-architecture`)

**Правила:**

- ✅ Domain → Domain (internal)
- ✅ Application → Domain (uses ports)
- ✅ Composition → All (assembles dependencies)
- ✅ Infrastructure → Domain (implements ports)
- ✅ Interfaces → All (entry points)

**Запрещённые импорты:**

- ❌ Domain → Application/Infrastructure/Composition
- ❌ Application → Infrastructure/Composition
- ❌ Infrastructure → Application/Composition

**Нарушение = Блокер PR**

**Файл:** [`docs/02-architecture/diagrams/foundation/27-import-matrix-enforcement.mmd`](../foundation/27-import-matrix-enforcement.mmd)

______________________________________________________________________

### 1.4 Medallion Architecture Overview

> **Diagram:** See [`03-medallion-data-flow.mmd`](../architecture/03-medallion-data-flow.mmd)

**Приоритет:** 9.38 | **Тип:** Flowchart

**Описание:**

Bronze → Silver → Gold уровни хранения данных.

**Bronze Layer:**

- Format: JSONL + zstd compression
- Storage: Local FileSystem
- Retention: 90 days → Archive
- Idempotency: Append-only
- Path: `bronze/v1/{provider}/{entity}/{date}/`

**Silver Layer:**

- Format: Delta Lake
- Storage: Local Delta Tables
- Retention: Permanent
- Idempotency: Merge by `content-hash`
- ACID: Required
- Operations: MERGE, APPEND, DELETE

**Gold Layer:**

- Format: Delta Lake (Validated)
- Storage: Local Delta Tables
- Retention: Permanent
- Idempotency: SCD2 or Overwrite
- Schema: Strict (только scalar types)
- Operations: OVERWRITE, APPEND, SCD2

**Key Features:**

- Content Hash Deduplication
- ACID Transactions
- Delta Time Travel (7-day history)
- VACUUM cleanup (weekly)

**Файл:** [`docs/02-architecture/diagrams/architecture/03-medallion-data-flow.mmd`](../architecture/03-medallion-data-flow.mmd)

______________________________________________________________________

## 2. Потоки Данных

### 2.1 Complete Pipeline Flow

[Complete Pipeline Flow](../foundation/08-complete-etl-workflow.mmd)

**Приоритет:** 9.56 | **Тип:** Flowchart

**Описание:**

End-to-end поток данных от API провайдера до Gold layer.

**Этапы выполнения:**

1. **Preflight Checks**

   - Infrastructure validation
   - Provider health check
   - Storage availability

1. **Lock Acquisition**

   - Acquire runtime lock (process-local in Local-Only profile)
   - Start heartbeat (30s interval)

1. **Medallion Clear** (зависит от run-type)

   - Incremental: Load checkpoint
   - Backfill: Clear Silver + Gold
   - Rebuild: Clear Silver + Gold

1. **Batch Execution Loop**

   - Fetch batch from provider
   - Handle rate limits (429)
   - Retry on errors (5xx)
   - Circuit breaker protection

1. **Transform Phase** (Bronze → Silver)

   - Apply BaseTransformer
   - Schema validation
   - DQ checks
   - Quarantine failures
   - Calculate content-hash

1. **Write Bronze**

   - JSONL + zstd compression
   - Write -metadata.yaml

1. **Write Silver**

   - Delta merge by content-hash
   - ACID commit
   - Deduplication

1. **Write Gold**

   - Filter JSON fields
   - Strict validation
   - Write mode (SCD2/Overwrite/Append)

1. **Batch Completion**

   - Record metrics
   - Save checkpoint
   - Memory check → Adaptive batch size

1. **Postrun Operations**

   - DQ analysis (Bronze/Silver/Gold)
   - Check DQ thresholds
   - Generate DQ report
   - VACUUM Delta tables
   - Cleanup resources
   - Release lock

**Error Handling:**

- Rate Limit: Exponential backoff
- Server Error: Retry logic (max 3)
- DQ Error: Quarantine (soft: >5%, hard: >20%)
- Circuit Breaker: 5 consecutive → Open (5 min)

**Graceful Shutdown:**

- SIGTERM → Finish current batch → Save checkpoint → Exit(0)

**Файл:** [`docs/02-architecture/diagrams/foundation/08-complete-etl-workflow.mmd`](../foundation/08-complete-etl-workflow.mmd)

______________________________________________________________________

### 2.2 Silver Merge Operation

[Silver Merge Operation](../foundation/19-delta-lake-write-sequence.mmd)

**Приоритет:** 8.31 | **Тип:** Flowchart

**Описание:**

Delta merge by content-hash — критическая операция для idempotency.

**Процесс:**

1. **Batch Preparation**

   - Calculate content-hash: `sha256(provider + canonical-json(record))`
   - Normalize data (NaN→null, round floats, ISO dates)
   - Attach persisted semantic system fields (`entity_id`, `content_hash`,
     `_source`, `_index`) and publish occurrence-scoped provenance separately
     via sidecar/control-plane artifacts

1. **Table Check**

   - Если таблицы нет → Create Delta table
   - Если есть → MERGE operation

1. **Delta MERGE**

   ```sql
   MERGE INTO silver-table
   USING new-batch
   ON silver-table.content-hash = new-batch.content-hash
   WHEN MATCHED THEN UPDATE SET *
   WHEN NOT MATCHED THEN INSERT *
   ```

1. **ACID Transaction**

   - Begin transaction
   - Acquire table lock
   - Execute merge
   - Validate constraints
   - Commit or Rollback

1. **Deduplication Check**

   - Count duplicates by content-hash
   - Emit metrics

**Key Properties:**

- ✓ Idempotent by content-hash
- ✓ ACID guaranteed
- ✓ Automatic deduplication
- ✓ Optimistic concurrency

**Файл:** [`docs/02-architecture/diagrams/foundation/19-delta-lake-write-sequence.mermaid`](../foundation/19-delta-lake-write-sequence.mmd)

______________________________________________________________________

## 3. Компонентные Диаграммы

### 3.1 Domain Model Overview

[Domain Model](../foundation/13-domain-models-relationship.mmd)

**Приоритет:** 9.31 | **Тип:** Class Diagram

**Описание:**

Representative карта доменной модели с DDD aggregates, entity families и value-object families.

**DDD Aggregates (Root Entities):**

- **PipelineRun** (574 LOC) - Aggregate root для pipeline execution
- **Batch** (536 LOC) - Aggregate root для batch processing
- **QuarantineEntry** (517 LOC) - Aggregate root для quarantine

**Entities:**

- ChemblActivity, UniProtProtein, PubChemMolecule
- CrossRefWork, OpenAlexWork, PubMedArticle, SemanticScholarPaper

**Value Objects:**

- Activity, DQMetrics, RunContext, StageResult, BatchRecord
- CompoundIds, TaxonomyId, Identifiers

**Domain Services:**

- DefaultDataNormalizer, EntityIdentityGenerator
- UnitConverter, ActivityAggregator, ValueValidator

**Файл:** [`docs/02-architecture/diagrams/foundation/13-domain-models-relationship.mmd`](../foundation/13-domain-models-relationship.mmd)

______________________________________________________________________

### 3.2 Ports Architecture

[Ports Architecture](../foundation/26-hexagonal-ports-adapters.mmd)

**Приоритет:** 9.25 | **Тип:** Interface Diagram

**Описание:**

Port protocol families — контракты между Domain и Infrastructure.

**Категории портов:**

1. **Data Flow (7):** DataSourcePort, FilterableDataSourcePort, BronzeStoragePort, SilverStoragePort, GoldStoragePort, MergedStoragePort, DeltaReaderPort
1. **Coordination (3):** LockPort, CheckpointPort, ShutdownPort
1. **Resilience (2):** RateLimiterPort, CircuitBreakerPort
1. **Observability (4):** TracingPort, MetricsPort, LoggerPort, DQMonitorPort
1. **Validation (3):** GoldValidatorPort, SilverValidatorPort, ValidationPort
1. **Quarantine (2):** QuarantinePort, HealthCheckPort
1. **Normalization (5):** DataNormalizationPort, UnitConverterPort, ValueValidatorPort, ActivityAggregatorPort, OutlierFilterPort
1. **DQ Reporting (4):** BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort
1. **Memory & PII (2):** MemoryMonitorPort, PiiHasherPort
1. **Metadata & Audit (3):** MetadataWriterPort, MetadataCoordinatorPort, AuditPort
1. **Other (3):** HealthMonitorPort, IDMappingPort, JsonEncoderPort

**Implementations:**

- ChemblAdapter → DataSourcePort
- MemoryLock → LockPort
- BronzeWriter → BronzeStoragePort
- SilverWriter → SilverStoragePort
- GoldWriter / composite write path → GoldStoragePort / MergedStoragePort
- StructlogLogger → LoggerPort
- NoOpTracing/NoOpMetrics → Null Object Pattern

**Файл:** [`docs/02-architecture/diagrams/foundation/26-hexagonal-ports-adapters.mmd`](../foundation/26-hexagonal-ports-adapters.mmd)

______________________________________________________________________

### 3.3 Pipeline Core Components

[Pipeline Core Components](../foundation/40-application-core-collaboration.mmd)

**Приоритет:** 9.06 | **Тип:** Component Diagram

**Описание:**

Сердце application layer — PipelineRunner и его компоненты.

**Core Components:**

1. **PipelineRunner** (189 LOC)

   - Orchestrates: preflight → execution → postrun
   - Uses RunnerServices bundle

1. **BatchExecutor** (264 LOC)

   - Execute loop: fetch → process → adapt batch size
   - Loads checkpoint for incremental runs

1. **BatchProcessingService** (178 LOC)

   - Orchestrates: source metadata → bronze write → transform → concurrent silver/gold writes

1. **BatchTransformer** (220 LOC)

   - Applies BaseTransformer
   - Schema validation
   - DQ checks
   - Quarantine handling

1. **BatchWriter** (562 LOC)

   - Lock validation
   - Writes to Bronze/Silver/Gold

1. **BatchMetricsRecorderService** (130 LOC)

   - Records start/success/failure
   - Emits to Prometheus

**Supporting Managers:**

- LockRuntimeService, CheckpointRuntimeService, QuarantineRuntimeService, MemoryMonitor

**Services:**

- PreflightService, PostrunService, PipelineObserver

**Файл:** [`docs/02-architecture/diagrams/foundation/40-application-core-collaboration.mermaid`](../foundation/40-application-core-collaboration.mmd)

______________________________________________________________________

## 4. Паттерны и Механизмы

### 4.1 Error Classification

[Error Classification](../foundation/41-error-classification-tree.mmd)

**Приоритет:** 8.94 | **Тип:** Flowchart

**Описание:**

Стратегия обработки ошибок: Critical / Recoverable / Data Quality.

**Critical Errors** (Fail immediately):

- HTTP 401/403 (Authentication)
- Schema mismatch (Gold layer)
- DB unavailable
- → Cleanup → Exit(1)

**Recoverable Errors** (Retry with backoff):

- HTTP 429 Rate Limit
- HTTP 5xx Server Errors
- Network Timeout
- → Retry (max 3) → Exponential Backoff → Jitter

**Data Quality Errors** (Quarantine):

- Invalid SMILES
- Missing required field
- Out of range value
- → Quarantine record
- → Soft threshold (>5%): Warning
- → Hard threshold (>20%): Fail batch

**Circuit Breaker:**

- 5 consecutive failures → Open (5 min)
- Half-Open: Send probe
- Probe success → Closed

**Exception Hierarchy:**

- BioETLError (base)
  - CriticalError (401/403, schema violation)
  - RecoverableError (429, 5xx)
  - DataQualityError (invalid data)

**Файл:** [`docs/02-architecture/diagrams/foundation/41-error-classification-tree.mermaid`](../foundation/41-error-classification-tree.mmd)

______________________________________________________________________

### 4.2 Retry Mechanism

[Retry Mechanism](../foundation/04-error-flow.mmd)

**Приоритет:** 8.63 | **Тип:** Activity Diagram

**Описание:**

Exponential backoff с jitter для recoverable errors.

**Algorithm:**

```
delay = (backoff-factor ^ retry-count) * base-delay + random(jitter-min, jitter-max)
```

**Configuration:**

- max-retries = 3
- base-delay = 1.0 second
- backoff-factor = 2.0 (exponential)
- jitter-min = 0.1 seconds
- jitter-max = 0.5 seconds

**Retry Delays:**

- Attempt 2: 2^1 * 1.0 + jitter ≈ 2.3s
- Attempt 3: 2^2 * 1.0 + jitter ≈ 4.4s
- Attempt 4: 2^3 * 1.0 + jitter ≈ 8.2s

**Retryable Errors:**

- 429 Rate Limit
- 5xx Server Error
- Network Timeout
- Connection Reset

**Non-Retryable Errors:**

- 401/403 Auth
- 400 Bad Request
- 404 Not Found

**Файл:** [`docs/02-architecture/diagrams/foundation/04-error-flow.mermaid`](../foundation/04-error-flow.mmd)

______________________________________________________________________

### 4.3 Circuit Breaker States

[Circuit Breaker States](../foundation/07-circuit-breaker-states.mmd)

**Приоритет:** 8.75 | **Тип:** State Diagram

**Описание:**

Fault tolerance pattern для защиты от каскадных сбоев.

**States:**

1. **CLOSED** (Normal operation)

   - Allow all requests
   - Track failure count
   - Reset on success
   - → 5 consecutive failures → OPEN

1. **OPEN** (Fail fast)

   - Block all requests
   - Return error immediately
   - Start timeout timer (5 min)
   - → Timeout expires → HALF-OPEN

1. **HALF-OPEN** (Testing recovery)

   - Allow 1 probe request
   - Block other requests
   - → Probe succeeds → CLOSED
   - → Probe fails → OPEN

**Configuration:**

- failure-threshold: 5
- timeout: 300s (5 minutes)
- probe-count: 1

**Metrics:**

- `circuit-breaker-trips-total` (counter)
- `circuit-breaker-state` (gauge)
- `circuit-breaker-failure-count` (gauge)

**Файл:** [`docs/02-architecture/diagrams/foundation/07-circuit-breaker-states.mermaid`](../foundation/07-circuit-breaker-states.mmd)

______________________________________________________________________

### 4.4 Graceful Shutdown

[Graceful Shutdown](../foundation/05-pipeline-lifecycle-states.mmd)

**Приоритет:** 8.19 | **Тип:** Sequence Diagram

**Описание:**

Корректное завершение при получении SIGTERM/SIGINT.

**Sequence:**

1. OS → SignalHandler: SIGTERM or SIGINT
1. Shutdown.trigger-shutdown()
1. Set `-shutting-down = True`
1. Notify PipelineRunner
1. Stop fetching new batches
1. **Finish current batch** (Transform → Write Bronze/Silver/Gold)
1. Save checkpoint (current state)
1. Stop heartbeat
1. Release lock
1. Cleanup resources (aclose())
1. Exit(0)

**Key Guarantees:**

- ✓ Current batch commits atomically
- ✓ No data loss
- ✓ Resume from checkpoint
- ✓ Lock released properly
- ✓ Resources cleaned up

**Checkpoint State:**

- run-id
- last-offset
- processed-count
- last-batch-id
- timestamp

**Файл:** [`docs/02-architecture/diagrams/foundation/05-pipeline-lifecycle-states.mermaid`](../foundation/05-pipeline-lifecycle-states.mmd)

______________________________________________________________________

## 5. Конфигурация и Схемы

### 5.1 PipelineConfig Structure

[PipelineConfig Structure](../foundation/46-yaml-config-resolution.mmd)

**Приоритет:** 8.13 | **Тип:** Class Diagram

**Описание:**

Complete pipeline configuration с 100+ полями.

**Main Components:**

- **PipelineConfig** (969 LOC)

  - pipeline-name, provider, entity, version
  - source, sink, transforms
  - dq-config, filters, batch-size

- **SourceConfig**

  - type: api | file | database
  - endpoint, auth-type
  - rate-limit, pagination

- **SinkConfig**

  - bronze: BronzeConfig
  - silver: SilverConfig (write-mode: MERGE/APPEND/DELETE)
  - gold: GoldConfig (write-mode: OVERWRITE/APPEND/SCD2)

- **DQConfig** (292 LOC)

  - soft-fail-threshold: 0.05 (5%)
  - hard-fail-threshold: 0.20 (20%)
  - enabled-checks, rules

- **RuntimeConfig**

  - run-type: incremental | backfill | rebuild
  - limit, dry-run, data-dir
  - log-level, filters
  - clear-policy, lock-ttl

**Loading:**

- YAML: `configs/entities/{provider}/{entity}.yaml`
- Example: `configs/entities/chembl/activity.yaml`

**CLI:**

```bash
bioetl run --pipeline chembl_activity \
  --run-type incremental \
  --limit 1000 \
  --data-dir /path/to/data
```

**Файл:** [`docs/02-architecture/diagrams/foundation/46-yaml-config-resolution.mermaid`](../foundation/46-yaml-config-resolution.mmd)

______________________________________________________________________

## Приложения

### Полный Список Диаграмм

См. [`diagrams/README.md`](../README.md) для каталога диаграмм.

### TOP-50 Таблица

*(Файл `top-50-diagrams.md` удалён как устаревший. См. [`diagrams/README.md`](../README.md) для актуального каталога.)*

### Mermaid Исходники

Все `.mermaid` файлы находятся в [`docs/02-architecture/diagrams/`](../README.md).

### Рендеринг

Скрипт рендеринга: [`render.sh`](../tooling/render.sh) или `make render-diagrams`.

______________________________________________________________________

*Создано автоматически | Claude Code | 2026-01-20*
