# Architecture Diagrams - BioETL

*Версия: 1.0 | Дата: 2026-01-20 | Статус: Активная*

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

[Five Layer Architecture](diagrams/mermaid/01_five_layer_architecture.mmd)

**Приоритет:** 9.69 | **Тип:** Component Diagram

**Описание:**

Фундаментальная архитектура проекта BioETL с пятью чёткими слоями:

- **Domain Layer** - Чистая бизнес-логика без I/O:

  - 3 DDD Aggregates (PipelineRun, Batch, QuarantineEntry)
  - 26 Ports (Protocol interfaces)
  - 9 Entities (ChemblActivity, UniProtProtein и др.)
  - 11 Value Objects
  - 6 Domain Services

- **Application Layer** - Use Cases и оркестрация:

  - PipelineRunner, BatchExecutor, RecordProcessor
  - 30+ Pipeline implementations
  - 14 Application Services

- **Composition Layer** - Dependency Injection:

  - bootstrap_pipeline() - Composition Root
  - 8 Factories
  - PipelineRegistry

- **Infrastructure Layer** - Адаптеры:

  - 3 Storage Writers (Bronze/Silver/Gold)
  - 7 Provider Adapters
  - HTTP Infrastructure

- **Interfaces Layer** - Entry Points:

  - CLI (11+ commands)

**Ключевые правила:**

- ❌ Domain НЕ импортирует Application/Infrastructure
- ✅ Infrastructure реализует Domain Ports
- ✅ Composition собирает зависимости

**Файл:** [`docs/02-architecture/diagrams/mermaid/01_five_layer_architecture.mmd`](diagrams/mermaid/01_five_layer_architecture.mmd)

______________________________________________________________________

### 1.2 Hexagonal Architecture Overview

[Hexagonal Architecture](diagrams/mermaid/03_hexagonal_architecture.mmd)

**Приоритет:** 9.50 | **Тип:** C4 Context Diagram

**Описание:**

Ports & Adapters паттерн - ключевой архитектурный принцип проекта.

**Inbound Adapters:**

- CLI Interface (Click commands)

**Outbound Adapters:**

- 7 Provider Adapters (ChEMBL, PubChem, UniProt, CrossRef, OpenAlex, PubMed, SemanticScholar)
- Storage Adapters (BronzeWriter, SilverWriter, GoldWriter)
- Observability Adapters (StructlogLogger, PrometheusMetrics, OTELTracer)
- Coordination Adapters (MemoryLock, CheckpointAdapter, QuarantineAdapter)

**Domain Core:**

- DDD Aggregates
- Entities
- Value Objects
- Domain Services

**26 Ports (Protocols):**

- DataSourcePort, StoragePort
- LockPort, CheckpointPort, QuarantinePort
- TracingPort, MetricsPort, LoggerPort
- И другие...

**Файл:** [`docs/02-architecture/diagrams/mermaid/03_hexagonal_architecture.mmd`](diagrams/mermaid/03_hexagonal_architecture.mmd)

______________________________________________________________________

### 1.3 Layer Dependency Matrix

[Layer Dependency Matrix](diagrams/mermaid/04_layer_dependency_matrix.mmd)

**Приоритет:** 9.44 | **Тип:** Matrix Diagram

**Описание:**

Матрица разрешённых импортов между слоями. Enforcement через:

- `tests/architecture/test_layer_contracts.py`
- `import-linter` configuration
- CI pipeline (`make arch-test`)

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

**Файл:** [`docs/02-architecture/diagrams/mermaid/04_layer_dependency_matrix.mmd`](diagrams/mermaid/04_layer_dependency_matrix.mmd)

______________________________________________________________________

### 1.4 Medallion Architecture Overview

[Medallion Architecture](diagrams/mermaid/05_medallion_architecture.mmd)

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
- Idempotency: Merge by `content_hash`
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

**Файл:** [`docs/02-architecture/diagrams/mermaid/05_medallion_architecture.mmd`](diagrams/mermaid/05_medallion_architecture.mmd)

______________________________________________________________________

## 2. Потоки Данных

### 2.1 Complete Pipeline Flow

[Complete Pipeline Flow](diagrams/mermaid/02_complete_pipeline_flow.mmd)

**Приоритет:** 9.56 | **Тип:** Flowchart

**Описание:**

End-to-end поток данных от API провайдера до Gold layer.

**Этапы выполнения:**

1. **Preflight Checks**

   - Infrastructure validation
   - Provider health check
   - Storage availability

1. **Lock Acquisition**

   - Acquire distributed lock
   - Start heartbeat (30s interval)

1. **Medallion Clear** (зависит от run_type)

   - Incremental: Load checkpoint
   - Backfill: Clear Silver
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
   - Calculate content_hash

1. **Write Bronze**

   - JSONL + zstd compression
   - Write \_metadata.yaml

1. **Write Silver**

   - Delta merge by content_hash
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

**Файл:** [`docs/02-architecture/diagrams/mermaid/02_complete_pipeline_flow.mmd`](diagrams/mermaid/02_complete_pipeline_flow.mmd)

______________________________________________________________________

### 2.2 Silver Merge Operation

[Silver Merge Operation](diagrams/mermaid/22_silver_merge_operation.mmd)

**Приоритет:** 8.31 | **Тип:** Flowchart

**Описание:**

Delta merge by content_hash — критическая операция для idempotency.

**Процесс:**

1. **Batch Preparation**

   - Calculate content_hash: `sha256(provider + canonical_json(record))`
   - Normalize data (NaN→null, round floats, ISO dates)
   - Add metadata (\_run_id, \_ingestion_ts, etc.)

1. **Table Check**

   - Если таблицы нет → Create Delta table
   - Если есть → MERGE operation

1. **Delta MERGE**

   ```sql
   MERGE INTO silver_table
   USING new_batch
   ON silver_table.content_hash = new_batch.content_hash
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

   - Count duplicates by content_hash
   - Emit metrics

**Key Properties:**

- ✓ Idempotent by content_hash
- ✓ ACID guaranteed
- ✓ Automatic deduplication
- ✓ Optimistic concurrency

**Файл:** [`docs/02-architecture/diagrams/mermaid/22_silver_merge_operation.mmd`](diagrams/mermaid/22_silver_merge_operation.mmd)

______________________________________________________________________

## 3. Компонентные Диаграммы

### 3.1 Domain Model Overview

[Domain Model](diagrams/mermaid/06_domain_model_overview.mmd)

**Приоритет:** 9.31 | **Тип:** Class Diagram

**Описание:**

Полная доменная модель с DDD Aggregates, Entities, Value Objects.

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

- DataNormalizationService, IdentityService
- UnitConverter, ActivityAggregator, ValueValidator

**Файл:** [`docs/02-architecture/diagrams/mermaid/06_domain_model_overview.mmd`](diagrams/mermaid/06_domain_model_overview.mmd)

______________________________________________________________________

### 3.2 Ports Architecture

[Ports Architecture](diagrams/mermaid/07_ports_architecture.mmd)

**Приоритет:** 9.25 | **Тип:** Interface Diagram

**Описание:**

26 Protocol interfaces — контракты между Domain и Infrastructure.

**Категории портов:**

1. **Data Flow (4):** DataSourcePort, FilterableDataSourcePort, StoragePort, DeltaReaderPort
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
- BronzeWriter/SilverWriter/GoldWriter → StoragePort
- StructlogLogger → LoggerPort
- NoOpTracing/NoOpMetrics → Null Object Pattern

**Файл:** [`docs/02-architecture/diagrams/mermaid/07_ports_architecture.mmd`](diagrams/mermaid/07_ports_architecture.mmd)

______________________________________________________________________

### 3.3 Pipeline Core Components

[Pipeline Core Components](diagrams/mermaid/10_pipeline_core_components.mmd)

**Приоритет:** 9.06 | **Тип:** Component Diagram

**Описание:**

Сердце application layer — PipelineRunner и его компоненты.

**Core Components:**

1. **PipelineRunner** (189 LOC)

   - Orchestrates: preflight → execution → postrun
   - Uses RunnerServices bundle

1. **BatchExecutor** (786 LOC)

   - Execute loop: fetch → process → adapt batch size
   - Loads checkpoint for incremental runs

1. **RecordProcessor** (222 LOC)

   - Delegates: transform → write_bronze → write_silver → write_gold

1. **BatchTransformer** (404 LOC)

   - Applies BaseTransformer
   - Schema validation
   - DQ checks
   - Quarantine handling

1. **BatchWriter** (562 LOC)

   - Lock validation
   - Writes to Bronze/Silver/Gold

1. **BatchMetricsRecorder** (130 LOC)

   - Records start/success/failure
   - Emits to Prometheus

**Supporting Managers:**

- LockManager, CheckpointManager, QuarantineManager, MemoryMonitor

**Services:**

- PreflightService, PostrunService, PipelineObserver

**Файл:** [`docs/02-architecture/diagrams/mermaid/10_pipeline_core_components.mmd`](diagrams/mermaid/10_pipeline_core_components.mmd)

______________________________________________________________________

## 4. Паттерны и Механизмы

### 4.1 Error Classification

[Error Classification](diagrams/mermaid/12_error_classification.mmd)

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

**Файл:** [`docs/02-architecture/diagrams/mermaid/12_error_classification.mmd`](diagrams/mermaid/12_error_classification.mmd)

______________________________________________________________________

### 4.2 Retry Mechanism

[Retry Mechanism](diagrams/mermaid/17_retry_mechanism.mmd)

**Приоритет:** 8.63 | **Тип:** Activity Diagram

**Описание:**

Exponential backoff с jitter для recoverable errors.

**Algorithm:**

```
delay = (backoff_factor ^ retry_count) * base_delay + random(jitter_min, jitter_max)
```

**Configuration:**

- max_retries = 3
- base_delay = 1.0 second
- backoff_factor = 2.0 (exponential)
- jitter_min = 0.1 seconds
- jitter_max = 0.5 seconds

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

**Файл:** [`docs/02-architecture/diagrams/mermaid/17_retry_mechanism.mmd`](diagrams/mermaid/17_retry_mechanism.mmd)

______________________________________________________________________

### 4.3 Circuit Breaker States

[Circuit Breaker States](diagrams/mermaid/15_circuit_breaker_states.mmd)

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
   - → Timeout expires → HALF_OPEN

1. **HALF_OPEN** (Testing recovery)

   - Allow 1 probe request
   - Block other requests
   - → Probe succeeds → CLOSED
   - → Probe fails → OPEN

**Configuration:**

- failure_threshold: 5
- timeout: 300s (5 minutes)
- probe_count: 1

**Metrics:**

- `circuit_breaker_trips_total` (counter)
- `circuit_breaker_state` (gauge)
- `circuit_breaker_failure_count` (gauge)

**Файл:** [`docs/02-architecture/diagrams/mermaid/15_circuit_breaker_states.mmd`](diagrams/mermaid/15_circuit_breaker_states.mmd)

______________________________________________________________________

### 4.4 Graceful Shutdown

[Graceful Shutdown](diagrams/mermaid/24_graceful_shutdown.mmd)

**Приоритет:** 8.19 | **Тип:** Sequence Diagram

**Описание:**

Корректное завершение при получении SIGTERM/SIGINT.

**Sequence:**

1. OS → SignalHandler: SIGTERM or SIGINT
1. Shutdown.trigger_shutdown()
1. Set `_shutting_down = True`
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

- run_id
- last_offset
- processed_count
- last_batch_id
- timestamp

**Файл:** [`docs/02-architecture/diagrams/mermaid/24_graceful_shutdown.mmd`](diagrams/mermaid/24_graceful_shutdown.mmd)

______________________________________________________________________

## 5. Конфигурация и Схемы

### 5.1 PipelineConfig Structure

[PipelineConfig Structure](diagrams/mermaid/25_pipeline_config_structure.mmd)

**Приоритет:** 8.13 | **Тип:** Class Diagram

**Описание:**

Complete pipeline configuration с 100+ полями.

**Main Components:**

- **PipelineConfig** (969 LOC)

  - pipeline_name, provider, entity, version
  - source, sink, transforms
  - dq_config, filters, batch_size

- **SourceConfig**

  - type: api | file | database
  - endpoint, auth_type
  - rate_limit, pagination

- **SinkConfig**

  - bronze: BronzeConfig
  - silver: SilverConfig (write_mode: MERGE/APPEND/DELETE)
  - gold: GoldConfig (write_mode: OVERWRITE/APPEND/SCD2)

- **DQConfig** (292 LOC)

  - soft_fail_threshold: 0.05 (5%)
  - hard_fail_threshold: 0.20 (20%)
  - enabled_checks, rules

- **RuntimeConfig**

  - run_type: incremental | backfill | rebuild
  - limit, dry_run, data_dir
  - log_level, filters
  - clear_policy, lock_ttl

**Loading:**

- YAML: `configs/pipelines/{provider}/{entity}.yaml`
- Example: `configs/pipelines/chembl/activity.yaml`

**CLI:**

```bash
bioetl run chembl_activity \
  --run-type incremental \
  --limit 1000 \
  --data-dir /path/to/data
```

**Файл:** [`docs/02-architecture/diagrams/mermaid/25_pipeline_config_structure.mmd`](diagrams/mermaid/25_pipeline_config_structure.mmd)

______________________________________________________________________

## Приложения

### Полный Список Диаграмм

См. [`diagram-catalog.md`](diagrams/mermaid/diagram-catalog.md) для каталога диаграмм.

### TOP-50 Таблица

См. [`top-50-diagrams.md`](diagrams/mermaid/top-50-diagrams.md) для полной таблицы с приоритетами и обоснованиями.

### Mermaid Исходники

Все `.mermaid` файлы находятся в [`docs/02-architecture/diagrams/mermaid/`](diagrams/mermaid/).

### Рендеринг

Скрипт рендеринга: [`render_diagrams.sh`](diagrams/mermaid/render_diagrams.sh), [`render_diagrams.py`](diagrams/mermaid/render_diagrams.py)

______________________________________________________________________

*Создано автоматически | Claude Code | 2026-01-20*
