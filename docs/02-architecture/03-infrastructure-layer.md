______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Слой Infrastructure (Инфраструктура)

**Расположение:** `src/bioetl/infrastructure/`

## 1. Назначение

Слой `Infrastructure` содержит конкретные реализации **портов**, определённых в слое `Domain`. Он отвечает за всё взаимодействие с внешним миром: базы данных, файловые системы, сетевые API, брокеры сообщений и т.д.

Этот слой является "мостом" между чистой бизнес-логикой и реальными технологиями.

**Ключевые характеристики:**

- **Реализация портов:** Классы в этом слое реализуют `Protocol` из `domain.ports`.
- **Зависимости:** Здесь находятся все "грязные" детали: HTTP-клиенты, коннекторы к БД, специфичные SDK.
- **Изменчивость:** Этот слой наиболее подвержен изменениям при смене технологий, но текущий поддерживаемый runtime в проекте остаётся Local-Only.

**Центральные реализации:** `BronzeWriter`, `SilverWriter`, `GoldWriter` (medallion storage), `TokenBucketRateLimiter` и `CircuitBreakerGuard` (HTTP resilience), `MemoryLock` (local-only locking).

## 2. Ключевые Компоненты

### 2.0. Additional Infrastructure Families

Помимо adapters/storage/validation, текущий infrastructure-слой включает несколько
устойчивых package families, которые полезно явно учитывать при навигации по коду:

- `control_plane/` — file-backed stores для run manifest, run ledger, lineage и effective-config artifacts.
- `adr/` — ADR-related infrastructure helpers и read models.
- `audit/` — audit/report support utilities.
- `export/` — export adapters и supporting services для Gold-facing outputs.
- `serialization/` — canonical serialization helpers и schema-aligned payload shaping.
- `system/` — system/runtime environment helpers.
- `time/` — time abstractions и runtime clock helpers.

### 2.1. `adapters/` — Адаптеры к Внешним API

**Расположение:** `src/bioetl/infrastructure/adapters/`

Содержит адаптеры для конкретных источников данных (ChEMBL, PubChem, UniProt и т.д.). Каждый адаптер — это класс, реализующий `DataSourcePort`.

Создание и настройка адаптеров централизованы в каноническом composition-path через
`DataSourceFactory`, `get_data_source_creator()` и `ProviderRegistry`.

Политика import surfaces для provider adapters:

- Для нового first-party кода предпочтителен import provider package root
  (например, `bioetl.infrastructure.adapters.pubmed`,
  `bioetl.infrastructure.adapters.semanticscholar`).
- `pubmed/client.py` и `semanticscholar/client.py` retired; package roots and
  `adapter.py` are the sanctioned import seams.
- Старые implementation-module paths (`pubmed.pubmed_client`,
  `semanticscholar.adapter`) не являются sanctioned import path для нового кода.

#### 2.1.1. Provider Adapter Package Contract

Package contract для `infrastructure/adapters/{provider}/` строится вокруг роли
адаптера в Hexagonal Architecture, а не вокруг искусственной симметрии между
провайдерами.

**Обязательный минимум для provider package:**

- `__init__.py` как package-root facade.
- Один явный adapter entrypoint для primary adapter surface. В текущем проекте это
  обычно `adapter.py` или `client.py`, в зависимости от provider package.
- Primary adapter class должен экспортироваться через provider package root; новый
  first-party код должен импортировать именно package root, а не implementation
  modules.

**Допустимые расширения внутри provider package:**

- `exceptions.py`, если есть transport/runtime-specific errors.
- `models.py` и узкие provider-local model modules.
- Модули вроде `query_builder.py`, `response_parser.py`, `response_mapper.py`,
  `fetch_flow.py`, `health_probe.py`, `*_adapter_mixin.py`, если они отражают
  устойчивую infrastructure-роль.
- Private underscored modules, если они остаются локальной реализацией package и не
  становятся новым public import surface.

**Чего в provider package быть не должно:**

- application transformers;
- composition factories или bootstrap wiring;
- domain aggregate/value-object implementation details;
- vague shared helpers вроде `utils.py`/`common.py`, если они фактически нужны
  нескольким провайдерам. Такие вещи должны жить в
  `bioetl.infrastructure.adapters.common` или других общих infrastructure seams.

**Growth path policy:**

- Малые provider packages могут оставаться почти single-entrypoint пакетами.
- Более зрелые пакеты могут расти через тематические модули: query/fetch,
  response parsing, fallback, health/retry, provider-local models.
- Рост должен идти по устойчивым темам, а не через случайное накопление helpers на
  одном уровне каталога.

**Sanctioned public adapter seams в текущем цикле:**

- PubMed: `bioetl.infrastructure.adapters.pubmed` and
  `bioetl.infrastructure.adapters.pubmed.adapter`.
- Semantic Scholar: `bioetl.infrastructure.adapters.semanticscholar` and
  `bioetl.infrastructure.adapters.semanticscholar.adapter`.
- `pubmed/client.py` и `semanticscholar/client.py` retired and must not be
  reintroduced as compatibility shims.
- `pubmed/pubmed_client.py` remains a legacy implementation-module path and is
  not sanctioned for new first-party imports.

Нормативные guardrails для этой политики закреплены в
`tests/architecture/test_adapter_contracts.py`,
`tests/architecture/test_retained_adapter_entrypoint_policy.py` и
[07-compatibility-facade-inventory.md](07-compatibility-facade-inventory.md).

**Обязанности адаптера:**

- Управление HTTP-соединениями через `UnifiedHTTPClient`.
- Обработка специфичных для API ошибок (например, `429 Rate Limit`).
- Преобразование ответа API в стандартизированный формат (словари Python).
- Реализация `health_check()` для проверки доступности API.

#### 2.1.2. Унифицированный HTTP-клиент

**Все адаптеры используют унифицированную HTTP-инфраструктуру:**

| Адаптер                    | Базовый класс                    | HTTP-клиент              | Примечание                                                                           |
| -------------------------- | -------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ |
| **ChemblAdapter**          | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, 15 entities, 0.1 rps (burst 1). Native pagination and filtering (without mixins) |
| **UniProtAdapter**         | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, 10 req/sec default (100 with API key). Mixin: `PaginatedFetcherMixin`    |
| **PubMedAdapter**          | `@dataclass` + `BaseHttpAdapter` | `UnifiedHTTPClient`      | Async HTTP, 3 req/sec                                                                |
| **PubChemAdapter**         | `BaseSyncAdapter`                | `pubchempy` + ThreadPool | Legacy sync, 5 req/sec. Mixin: `NotSupportedMultiFilterMixin`                        |
| **CrossRefAdapter**        | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, polite pool. Mixin: `PaginatedFetcherMixin`                              |
| **OpenAlexAdapter**        | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, 10 req/sec. Mixin: `PaginatedFetcherMixin`                               |
| **SemanticScholarAdapter** | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, 0.1 req/sec (1.0 with key). Mixin: `PaginatedFetcherMixin`               |

**Архитектура HTTP-адаптеров:**

```
┌─────────────────────────────────────────────────────────────┐
│                    DataSourcePort (Protocol)                 │
└─────────────────────────────────────────────────────────────┘
                              ▲
              ┌───────────────┴───────────────┐
              │                               │
┌─────────────────────────┐     ┌─────────────────────────┐
│    BaseHttpAdapter      │     │    BaseSyncAdapter      │
│  (UnifiedHTTPClient)    │     │  (ThreadPoolExecutor)   │
└─────────────────────────┘     └─────────────────────────┘
         ▲                                  ▲
    ┌────┴────┐                             │
    │         │                             │
ChemblAdapter UniProtAdapter          PubChemAdapter
PubMedAdapter                         (pubchempy)
```

**Ключевые компоненты `UnifiedHTTPClient`:**

- **Rate Limiter** (`TokenBucketRateLimiter`): Ограничение частоты запросов
- **Circuit Breaker** (`CircuitBreakerGuard`): Защита от каскадных отказов
- **Retry Logic**: Автоматические повторы с exponential backoff
- **Metrics**: Интеграция с `MetricsPort` для наблюдаемости

**Для sync-библиотек** (pubchempy, biopython) используется `BaseSyncAdapter`:

- `ThreadPoolExecutor` для изоляции блокирующего I/O
- Собственные `TokenBucketRateLimiter` и `CircuitBreakerGuard`
- Async-обёртка через `_run_in_executor()`

### 2.2. `storage/` — Адаптеры Хранилищ

**Расположение:** `src/bioetl/infrastructure/storage/`

Реализует narrow storage ports (`BronzeStoragePort`, `SilverStoragePort`, `GoldStoragePort`, `MergedStoragePort`) для работы с различными уровнями данных.

Реализация разделена на три writer-а. Конкретные классы остаются в корневых
модулях `bronze_writer.py`, `silver_writer.py` и `gold_writer.py`, а их
специализированные mixins, operations, runtime services и helpers сгруппированы
в подпакетах `bronze/`, `silver/` и `gold/`:

- **`BronzeWriter`** (`bronze_writer.py`): Запись сырых данных в формате JSONL + zstd. Atomic writes через temp file + rename, генерация checksums.
- **`SilverWriter`** (`silver_writer.py`): Запись в Delta Lake таблицы с наследованием от `BaseDeltaWriter`, ACID-транзакциями, логикой merge/upsert для идемпотентности, поддержкой Time Travel и 7-дневным VACUUM retention.
- **`GoldWriter`** (`gold_writer.py`): Запись бизнес-готовых данных с наследованием от `BaseDeltaWriter`, строгой валидацией через Pandera, поддержкой SCD Type 2 и контрактов данных.

#### 2.2.1. BronzeWriter Mixin Decomposition

| Файл                              | Класс/роль                     | Назначение                              |
| --------------------------------- | ------------------------------ | --------------------------------------- |
| `bronze_writer.py`                | `BronzeWriter`                 | Корневой concrete storage adapter       |
| `bronze/io_mixin.py`              | `BronzeWriterIOMixin`          | I/O операции (JSONL write, compression) |
| `bronze/read_cleanup_mixin.py`    | `BronzeWriterReadCleanupMixin` | Read и cleanup операции                 |
| `bronze/metadata_mixin.py`        | `BronzeWriterMetadataMixin`    | Генерация Bronze metadata sidecar       |
| `bronze/metrics_mixin.py`         | `BronzeWriterMetricsMixin`     | Метрики Bronze write операций           |
| `bronze/side_effects_mixin.py`    | `BronzeWriterSideEffectsMixin` | Side effects (checksum, audit)           |
| `bronze/validation_mixin.py`      | `BronzeWriterValidationMixin`  | Валидация входных данных                |
| `bronze/write_execution.py`       | Execution functions            | Atomic data и sidecar write flow        |
| `bronze/pipeline_helpers.py`      | Request/context helpers        | Подготовка и завершение write pipeline  |
| `bronze_write_result_helpers.py`  | Helper functions               | Формирование write result               |

#### 2.2.2. SilverWriter Mixin Decomposition

| Файл                                  | Класс/роль                      | Назначение                                 |
| ------------------------------------- | ------------------------------- | ------------------------------------------ |
| `silver_writer.py`                    | `SilverWriter`                  | Корневой concrete Delta storage adapter    |
| `silver/writer_runtime_facade.py`     | `SilverWriterRuntimeFacade`     | Делегирование в runtime operation services |
| `silver/delta_mixin.py`               | `SilverWriterDeltaMixin`        | Delta Lake write/merge operations          |
| `silver/merged_mixin.py`              | `SilverWriterMergedMixin`       | Merged-table write flow                    |
| `silver/metadata_mixin.py`            | `SilverWriterMetadataMixin`     | Silver metadata sidecar generation         |
| `silver/postwrite_mixin.py`           | `SilverWriterPostwriteMixin`    | Post-write operations                      |
| `silver/validation_mixin.py`          | `SilverWriterValidationMixin`   | Schema validation и data quality           |
| `silver/maintenance_mixin.py`         | `SilverWriterMaintenanceMixin`  | Maintenance operations                     |
| `silver/operations/`                  | Operation services              | Arrow, Delta, metadata, validation и postwrite operations |
| `silver/delta_helpers.py`             | Helper functions                | Delta Lake write helpers                   |
| `silver/merge_resilience_helpers.py`  | Helper functions                | Merge retry и resilience logic             |
| `silver/pipeline_helpers.py`          | Request/context helpers         | Pipeline-specific write flow               |
| `silver/runtime_helpers.py`           | Runtime service builders        | Runtime configuration и collaborator wiring |

#### 2.2.3. GoldWriter Mixin Decomposition

| Файл                          | Класс/роль                     | Назначение                             |
| ----------------------------- | ------------------------------ | -------------------------------------- |
| `gold_writer.py`              | `GoldWriter`                   | Корневой concrete Delta storage adapter |
| `gold/io_mixin.py`            | `GoldWriterIOMixin`            | I/O operations (Delta write)           |
| `gold/io_delta_mixins.py`     | Delta-specific mixins          | Merge, overwrite и SCD2 I/O            |
| `gold/metadata_mixin.py`      | `GoldWriterMetadataMixin`      | Gold metadata sidecar generation       |
| `gold/validation_mixin.py`    | `GoldWriterValidationMixin`    | Pandera schema validation              |
| `gold/read_cleanup_mixin.py`  | `GoldWriterReadCleanupMixin`   | Read и cleanup operations              |
| `gold/io_helpers.py`          | Helper functions               | I/O helper functions                   |
| `gold/metadata_audit.py`      | Audit helpers                  | Metadata audit trail                   |
| `gold/pipeline_helpers.py`    | Request/context helpers        | Pipeline-specific write flow           |
| `gold/runtime_helpers.py`     | Runtime service builders       | Runtime collaborator wiring            |
| `gold/metadata_operations.py` | Metadata operation functions   | Metadata sidecar write operations      |
| `gold/metadata_payloads.py`   | Payload builders               | Metadata payload normalization         |

#### 2.2.4. Storage Support

**Delta Lake infrastructure:**

| Файл                       | Компонент             | Назначение                                      |
| -------------------------- | --------------------- | ----------------------------------------------- |
| `base_delta_writer.py`     | `BaseDeltaWriter`     | Базовый класс для Silver/Gold writers           |
| `silver_writer.py`         | `SilverWriter`        | Канонический Delta Lake writer для Silver layer |
| `delta_reader.py`          | `DeltaReader`         | Чтение Delta Lake таблиц                        |
| `delta/arrow_converter.py` | `ArrowDataConverter`  | PyArrow conversion utilities                    |
| `delta/resilience.py`      | `AdaptiveRetryPolicy` | Retry/backoff policy objects for storage writes |
| `atomic.py`                | `atomic_write_text`   | Public atomic-write facade                      |
| `support/atomic_ops.py`    | `AtomicWriteGroup`    | Internal atomic file write and replace-retry    |

**Metadata infrastructure:**

| Файл                                    | Компонент             | Назначение                                                                              |
| --------------------------------------- | --------------------- | --------------------------------------------------------------------------------------- |
| `metadata_writer.py`                    | `MetadataWriter`      | Запись metadata sidecar YAML                                                            |
| `metadata/writer_operations.py`         | Internal operations   | Подготовка, telemetry, retry для metadata                                               |
| `metadata_builder.py`                   | `MetadataBuilder`     | Сборка metadata моделей                                                                 |
| `metadata/builder_base.py`              | Base builder          | Базовые функции сборки metadata                                                         |
| `metadata_builder_composite_helpers.py` | Compatibility wrapper | Transitional wrapper over canonical `bioetl.domain.behavior.composite_metadata_helpers` |

**Other storage:**

| Файл                           | Компонент                       | Назначение                           |
| ------------------------------ | ------------------------------- | ------------------------------------ |
| `support/retention.py`         | `RetentionPolicy`               | VACUUM retention и Delta maintenance |
| `support/checkpoint_writer.py` | `FileCompositeCheckpointWriter` | Запись composite checkpoint          |

#### 2.1.3. Adapter Support Infrastructure

**Error handling:**

| Файл                          | Компонент                | Назначение                                       |
| ----------------------------- | ------------------------ | ------------------------------------------------ |
| `adapter_error_classifier.py` | `AdapterErrorClassifier` | Классификация ошибок адаптеров (retryable и др.) |
| `adapter_error_mapper.py`     | `AdapterErrorMapper`     | Маппинг HTTP-ошибок на domain exceptions         |
| `error_handling.py`           | Error handling utilities | Общие утилиты обработки ошибок                   |

**Health monitoring:**

| Файл                       | Компонент            | Назначение                                        |
| -------------------------- | -------------------- | ------------------------------------------------- |
| `health_check_mixin.py`    | `HealthCheckMixin`   | Mixin для реализации `health_check()` в адаптерах |
| `health_check_contract.py` | `HealthCheckContext` | Контракт health check response                    |
| `health_probe_policy.py`   | `HealthProbePolicy`  | Политика health probes (interval, timeout)        |
| `health_status_policy.py`  | `HealthStatusPolicy` | Политика определения статуса по результатам       |

**Base classes and mixins:**

| Файл                           | Компонент                | Назначение                                   |
| ------------------------------ | ------------------------ | -------------------------------------------- |
| `base.py`                      | `BaseHttpAdapter`        | Базовый класс для async HTTP адаптеров       |
| `sync_base.py`                 | `BaseSyncAdapter`        | Базовый класс для sync адаптеров (pubchempy) |
| `base_metrics.py`              | Adapter metrics          | Метрики адаптеров (requests, latency)        |
| `filterable_mixin.py`          | `FilterableMixin`        | Mixin для фильтрации по ID-спискам           |
| `cached_bronze_data_source.py` | `CachedBronzeDataSource` | Кеширование Bronze данных                    |
| `validation.py`                | Validation utilities     | Валидация параметров адаптеров               |

**Subpackages:** `http/` (UnifiedHTTPClient, rate limiter, circuit breaker), `common/` (shared adapter utilities), `input/` (input data sources), `decorators/` (adapter decorators).

### 2.3. `locking/` — Реализация Блокировок

**Расположение:** `src/bioetl/infrastructure/locking/`

Содержит реализацию `LockPort` для координации пайплайнов.

**Текущая реализация (Local-Only):**

- **`MemoryLock`**: In-memory блокировка для локального развёртывания
- Однопроцессная изоляция (не распределённая)
- Поддержка exclusive-режима для backfill/rebuild

> **Note:** Redis-блокировки (ADR-003) superseded в пользу Local-Only стратегии.
> См. [ADR-010](decisions/ADR-010-local-only-deployment.md) для обоснования и текущего supported runtime.

`LockPort` сохраняется как архитектурная граница и для testability, но active project guidance использует только `MemoryLock`.

### 2.4. `checkpoint/` и `quarantine/`

- **`checkpoint/`**: Реализация `CheckpointPort` для сохранения состояния пайплайнов. Текущая реализация использует локальную файловую систему (`LocalCheckpointAdapter`). См. [ADR-010](decisions/ADR-010-local-only-deployment.md).
- **`quarantine/`**: Реализация `QuarantinePort` через unified Delta-backed адаптер (`UnifiedQuarantineAdapter`) для записи "плохих" данных.

### 2.5. `observability/` — Наблюдаемость

**Расположение:** `src/bioetl/infrastructure/observability/`

Содержит реализацию `MetricsPort` (например, с использованием библиотеки Prometheus Client) и настройку логирования (например, `structlog`).

## 3. Принципы Работы

- **Запрет на бизнес-логику:** В этом слое не должно быть бизнес-правил. Его задача — получить данные "как есть" или записать их "как сказано".
- **Инверсия зависимостей:** Классы из `Infrastructure` зависят от абстракций (`Protocol`) из `Domain`, а не наоборот. Это позволяет подменять реализации без изменения ядра системы.
- **Конфигурация:** Все необходимые параметры (API-ключи, пути, адреса серверов) адаптеры получают через DI из конфигурационных объектов.

______________________________________________________________________

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                                 | Текущий            | Следующий →                                |
| -------------------------------------------- | ------------------ | ------------------------------------------ |
| [Application Layer](02-application-layer.md) | **Infrastructure** | [Interfaces Layer](04-interfaces-layer.md) |

### Связанные Диаграммы

| Диаграмма              | Файл                                                                                                       | Описание                                         |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Infrastructure Classes | [10-infrastructure-layer-class-diagram.mmd](diagrams/foundation/10-infrastructure-layer-class-diagram.mmd) | Классы слоя Infrastructure                       |
| Provider Adapters      | [30-port-adapter-mapping.mmd](diagrams/foundation/30-port-adapter-mapping.mmd)                             | Обзор 7 external API adapters плюс `uniprot_idmapping` provider seam |
| HTTP Infrastructure    | [10-infrastructure-layer-class-diagram.mmd](diagrams/foundation/10-infrastructure-layer-class-diagram.mmd) | UnifiedHTTPClient, Rate Limiter, Circuit Breaker |
| Circuit Breaker        | [07-circuit-breaker-states.mmd](diagrams/foundation/07-circuit-breaker-states.mmd)                         | Состояния Circuit Breaker                        |
| Storage Architecture   | [19-delta-lake-write-sequence.mmd](diagrams/foundation/19-delta-lake-write-sequence.mmd)                   | Bronze, Silver, Gold writers                     |
| MemoryLock             | [16-memory-lock-class.mmd](diagrams/foundation/16-memory-lock-class.mmd)                                   | Класс MemoryLock                                 |

### Связанные ADR

| ADR                                                            | Тема                           |
| -------------------------------------------------------------- | ------------------------------ |
| [ADR-010](decisions/ADR-010-local-only-deployment.md)          | Local-Only deployment and single-process locking posture |
| [ADR-007](decisions/ADR-007-circuit-breaker-implementation.md) | Circuit Breaker Implementation |
| [ADR-010](decisions/ADR-010-local-only-deployment.md)          | Local-Only Deployment          |
| [ADR-017](decisions/ADR-017-observability-architecture.md)     | Observability Architecture     |

### Смежные Разделы Документации

- [Domain Layer](01-domain-layer.md) — порты, реализуемые адаптерами
- [Composition Layer](05-composition-layer.md) — фабрики создания адаптеров
- [API Reference: Infrastructure](../04-reference/api/infrastructure.md) — API документация слоя
- [RULES.md §3 "Ошибки"](../00-project/RULES.md) — классификация ошибок, retry logic
