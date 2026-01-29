# Architecture Diagrams - BioETL

*Версия: 1.0 | Дата: 2026-01-20 | Статус: Активная*

Комплексная система архитектурных диаграмм для понимания структуры, потоков данных и компонентов проекта BioETL.

---

## Содержание

1. [Обзорные Архитектурные Диаграммы](#1-обзорные-архитектурные-диаграммы)
2. [Потоки Данных](#2-потоки-данных)
3. [Компонентные Диаграммы](#3-компонентные-диаграммы)
4. [Паттерны и Механизмы](#4-паттерны-и-механизмы)
5. [Конфигурация и Схемы](#5-конфигурация-и-схемы)

---

## 1. Обзорные Архитектурные Диаграммы

### 1.1 Five Layer Architecture

[Five Layer Architecture](diagrams/01_five_layer_architecture.mmd)

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

**Файл:** [`docs/diagrams/mermaid/01_five_layer_architecture.mmd`](diagrams/01_five_layer_architecture.mmd)

---

### 1.2 Hexagonal Architecture Overview

[Hexagonal Architecture](diagrams/03_hexagonal_architecture.mmd)

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

**Файл:** [`docs/diagrams/mermaid/03_hexagonal_architecture.mmd`](diagrams/03_hexagonal_architecture.mmd)

---

### 1.3 Layer Dependency Matrix

[Layer Dependency Matrix](diagrams/04_layer_dependency_matrix.mmd)

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

**Файл:** [`docs/diagrams/mermaid/04_layer_dependency_matrix.mmd`](diagrams/04_layer_dependency_matrix.mmd)

---

### 1.4 Medallion Architecture Overview

[Medallion Architecture](diagrams/05_medallion_architecture.mmd)

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

**Файл:** [`docs/diagrams/mermaid/05_medallion_architecture.mmd`](diagrams/05_medallion_architecture.mmd)

---

## 2. Потоки Данных

### 2.1 Complete Pipeline Flow

[Complete Pipeline Flow](diagrams/02_complete_pipeline_flow.mmd)

**Приоритет:** 9.56 | **Тип:** Flowchart

**Описание:**

End-to-end поток данных от API провайдера до Gold layer.

**Этапы выполнения:**

1. **Preflight Checks**
   - Infrastructure validation
   - Provider health check
   - Storage availability

2. **Lock Acquisition**
   - Acquire distributed lock
   - Start heartbeat (30s interval)

3. **Medallion Clear** (зависит от run_type)
   - Incremental: Load checkpoint
   - Backfill: Clear Silver
   - Rebuild: Clear Silver + Gold

4. **Batch Execution Loop**
   - Fetch batch from provider
   - Handle rate limits (429)
   - Retry on errors (5xx)
   - Circuit breaker protection

5. **Transform Phase** (Bronze → Silver)
   - Apply BaseTransformer
   - Schema validation
   - DQ checks
   - Quarantine failures
   - Calculate content_hash

6. **Write Bronze**
   - JSONL + zstd compression
   - Write _metadata.yaml

7. **Write Silver**
   - Delta merge by content_hash
   - ACID commit
   - Deduplication

8. **Write Gold**
   - Filter JSON fields
   - Strict validation
   - Write mode (SCD2/Overwrite/Append)

9. **Batch Completion**
   - Record metrics
   - Save checkpoint
   - Memory check → Adaptive batch size

10. **Postrun Operations**
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

**Файл:** [`docs/diagrams/mermaid/02_complete_pipeline_flow.mmd`](diagrams/02_complete_pipeline_flow.mmd)

---

### 2.2 Silver Merge Operation

[Silver Merge Operation](diagrams/22_silver_merge_operation.mmd)

**Приоритет:** 8.31 | **Тип:** Flowchart

**Описание:**

Delta merge by content_hash — критическая операция для idempotency.

**Процесс:**

1. **Batch Preparation**
   - Calculate content_hash: `sha256(provider + canonical_json(record))`
   - Normalize data (NaN→null, round floats, ISO dates)
   - Add metadata (_run_id, _ingestion_ts, etc.)

2. **Table Check**
   - Если таблицы нет → Create Delta table
   - Если есть → MERGE operation

3. **Delta MERGE**
   ```sql
   MERGE INTO silver_table
   USING new_batch
   ON silver_table.content_hash = new_batch.content_hash
   WHEN MATCHED THEN UPDATE SET *
   WHEN NOT MATCHED THEN INSERT *
   ```

4. **ACID Transaction**
   - Begin transaction
   - Acquire table lock
   - Execute merge
   - Validate constraints
   - Commit or Rollback

5. **Deduplication Check**
   - Count duplicates by content_hash
   - Emit metrics

**Key Properties:**
- ✓ Idempotent by content_hash
- ✓ ACID guaranteed
- ✓ Automatic deduplication
- ✓ Optimistic concurrency

**Файл:** [`docs/diagrams/mermaid/22_silver_merge_operation.mmd`](diagrams/22_silver_merge_operation.mmd)

---

## 3. Компонентные Диаграммы

### 3.1 Domain Model Overview

[Domain Model](diagrams/06_domain_model_overview.mmd)

**Приоритет:** 9.31 | **Тип:** Class Diagram

**Описание:**

Полная доменная модель с DDD Aggregates, Entities, Value Objects.

**DDD Aggregates (Root Entities):**
- **PipelineRun** (567 LOC) - Aggregate root для pipeline execution
- **Batch** (537 LOC) - Aggregate root для batch processing
- **QuarantineEntry** (518 LOC) - Aggregate root для quarantine

**Entities:**
- ChemblActivity, UniProtProtein, PubChemMolecule
- CrossRefWork, OpenAlexWork, PubMedArticle, SemanticScholarPaper

**Value Objects:**
- Activity, DQMetrics, RunContext, StageResult, BatchRecord
- CompoundIds, TaxonomyId, Identifiers

**Domain Services:**
- DataNormalizationService, IdentityService
- UnitConverter, ActivityAggregator, ValueValidator

**Файл:** [`docs/diagrams/mermaid/06_domain_model_overview.mmd`](diagrams/06_domain_model_overview.mmd)

---

### 3.2 Ports Architecture

[Ports Architecture](diagrams/07_ports_architecture.mmd)

**Приоритет:** 9.25 | **Тип:** Interface Diagram

**Описание:**

26 Protocol interfaces — контракты между Domain и Infrastructure.

**Категории портов:**

1. **Data Flow (4):** DataSourcePort, FilterableDataSourcePort, StoragePort, DeltaReaderPort
2. **Coordination (3):** LockPort, CheckpointPort, ShutdownPort
3. **Resilience (2):** RateLimiterPort, CircuitBreakerPort
4. **Observability (4):** TracingPort, MetricsPort, LoggerPort, DQMonitorPort
5. **Validation (3):** GoldValidatorPort, SilverValidatorPort, ValidationPort
6. **Quarantine (2):** QuarantinePort, HealthCheckPort
7. **Normalization (5):** DataNormalizationPort, UnitConverterPort, ValueValidatorPort, ActivityAggregatorPort, OutlierFilterPort
8. **DQ Reporting (4):** BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort
9. **Memory & PII (2):** MemoryMonitorPort, PiiHasherPort
10. **Metadata & Audit (3):** MetadataWriterPort, MetadataCoordinatorPort, AuditPort
11. **Other (3):** HealthMonitorPort, IDMappingPort, JsonEncoderPort

**Implementations:**
- ChemblAdapter → DataSourcePort
- MemoryLock → LockPort
- BronzeWriter/SilverWriter/GoldWriter → StoragePort
- StructlogLogger → LoggerPort
- NoOpTracing/NoOpMetrics → Null Object Pattern

**Файл:** [`docs/diagrams/mermaid/07_ports_architecture.mmd`](diagrams/07_ports_architecture.mmd)

---

### 3.3 Pipeline Core Components

[Pipeline Core Components](diagrams/10_pipeline_core_components.mmd)

**Приоритет:** 9.06 | **Тип:** Component Diagram

**Описание:**

Сердце application layer — PipelineRunner и его компоненты.

**Core Components:**

1. **PipelineRunner** (186 LOC)
   - Orchestrates: preflight → execution → postrun
   - Uses RunnerServices bundle

2. **BatchExecutor** (150 LOC)
   - Execute loop: fetch → process → adapt batch size
   - Loads checkpoint for incremental runs

3. **RecordProcessor** (200 LOC)
   - Delegates: transform → write_bronze → write_silver → write_gold

4. **BatchTransformer** (200 LOC)
   - Applies BaseTransformer
   - Schema validation
   - DQ checks
   - Quarantine handling

5. **BatchWriter** (180 LOC)
   - Lock validation
   - Writes to Bronze/Silver/Gold

6. **BatchMetricsRecorder** (100 LOC)
   - Records start/success/failure
   - Emits to Prometheus

**Supporting Managers:**
- LockManager, CheckpointManager, QuarantineManager, MemoryMonitor

**Services:**
- PreflightService, PostrunService, PipelineObserver

**Файл:** [`docs/diagrams/mermaid/10_pipeline_core_components.mmd`](diagrams/10_pipeline_core_components.mmd)

---

## 4. Паттерны и Механизмы

### 4.1 Error Classification

[Error Classification](diagrams/12_error_classification.mmd)

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

**Файл:** [`docs/diagrams/mermaid/12_error_classification.mmd`](diagrams/12_error_classification.mmd)

---

### 4.2 Retry Mechanism

[Retry Mechanism](diagrams/17_retry_mechanism.mmd)

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

**Файл:** [`docs/diagrams/mermaid/17_retry_mechanism.mmd`](diagrams/17_retry_mechanism.mmd)

---

### 4.3 Circuit Breaker States

[Circuit Breaker States](diagrams/15_circuit_breaker_states.mmd)

**Приоритет:** 8.75 | **Тип:** State Diagram

**Описание:**

Fault tolerance pattern для защиты от каскадных сбоев.

**States:**

1. **CLOSED** (Normal operation)
   - Allow all requests
   - Track failure count
   - Reset on success
   - → 5 consecutive failures → OPEN

2. **OPEN** (Fail fast)
   - Block all requests
   - Return error immediately
   - Start timeout timer (5 min)
   - → Timeout expires → HALF_OPEN

3. **HALF_OPEN** (Testing recovery)
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

**Файл:** [`docs/diagrams/mermaid/15_circuit_breaker_states.mmd`](diagrams/15_circuit_breaker_states.mmd)

---

### 4.4 Graceful Shutdown

[Graceful Shutdown](diagrams/24_graceful_shutdown.mmd)

**Приоритет:** 8.19 | **Тип:** Sequence Diagram

**Описание:**

Корректное завершение при получении SIGTERM/SIGINT.

**Sequence:**

1. OS → SignalHandler: SIGTERM or SIGINT
2. Shutdown.trigger_shutdown()
3. Set `_shutting_down = True`
4. Notify PipelineRunner
5. Stop fetching new batches
6. **Finish current batch** (Transform → Write Bronze/Silver/Gold)
7. Save checkpoint (current state)
8. Stop heartbeat
9. Release lock
10. Cleanup resources (aclose())
11. Exit(0)

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

**Файл:** [`docs/diagrams/mermaid/24_graceful_shutdown.mmd`](diagrams/24_graceful_shutdown.mmd)

---

## 5. Конфигурация и Схемы

### 5.1 PipelineConfig Structure

[PipelineConfig Structure](diagrams/25_pipeline_config_structure.mmd)

**Приоритет:** 8.13 | **Тип:** Class Diagram

**Описание:**

Complete pipeline configuration с 100+ полями.

**Main Components:**

- **PipelineConfig** (106 LOC)
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

- **DQConfig** (78 LOC)
  - soft_fail_threshold: 0.05 (5%)
  - hard_fail_threshold: 0.20 (20%)
  - enabled_checks, rules

- **RuntimeConfig** (98 LOC)
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

**Файл:** [`docs/diagrams/mermaid/25_pipeline_config_structure.mmd`](diagrams/25_pipeline_config_structure.mmd)

---

## Приложения

### Полный Список Диаграмм

См. [`diagram-catalog.md`](diagrams/diagram-catalog.md) для каталога диаграмм.

### TOP-50 Таблица

См. [`top-50-diagrams.md`](diagrams/top-50-diagrams.md) для полной таблицы с приоритетами и обоснованиями.

### Mermaid Исходники

Все `.mermaid` файлы находятся в [`docs/02-architecture/diagrams/`](diagrams/).

### Рендеринг

Скрипт рендеринга: [`render_diagrams.sh`](diagrams/render_diagrams.sh), [`render_diagrams.py`](diagrams/render_diagrams.py)

---

*Создано автоматически | Claude Code | 2026-01-20*
