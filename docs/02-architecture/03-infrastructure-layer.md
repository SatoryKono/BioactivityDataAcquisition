# Слой Infrastructure (Инфраструктура)

**Расположение:** `src/bioetl/infrastructure/`

## 1. Назначение

Слой `Infrastructure` содержит конкретные реализации **портов**, определённых в слое `Domain`. Он отвечает за всё взаимодействие с внешним миром: базы данных, файловые системы, сетевые API, брокеры сообщений и т.д.

Этот слой является "мостом" между чистой бизнес-логикой и реальными технологиями.

**Ключевые характеристики:**

- **Реализация портов:** Классы в этом слое реализуют `Protocol` из `domain.ports`.
- **Зависимости:** Здесь находятся все "грязные" детали: HTTP-клиенты, коннекторы к БД, специфичные SDK.
- **Изменчивость:** Этот слой наиболее подвержен изменениям при смене технологий (например, переход с локальной ФС на объектное хранилище в будущем).

**Центральные реализации:** `BronzeWriter`, `SilverWriter`, `GoldWriter` (medallion storage), `TokenBucketRateLimiter` и `CircuitBreakerGuard` (HTTP resilience), `MemoryLock` (local-only locking).

## 2. Ключевые Компоненты

### 2.1. `adapters/` — Адаптеры к Внешним API

**Расположение:** `src/bioetl/infrastructure/adapters/`

Содержит адаптеры для конкретных источников данных (ChEMBL, PubChem, UniProt и т.д.). Каждый адаптер — это класс, реализующий `DataSourcePort`.

Создание и настройка адаптеров централизованы в [DataSourceRegistry](05-composition-layer.md#22-factories--фабрики-компонентов) слоя Composition.

**Обязанности адаптера:**

- Управление HTTP-соединениями через `UnifiedHTTPClient`.
- Обработка специфичных для API ошибок (например, `429 Rate Limit`).
- Преобразование ответа API в стандартизированный формат (словари Python).
- Реализация `health_check()` для проверки доступности API.

#### 2.1.1. Унифицированный HTTP-клиент

**Все адаптеры используют унифицированную HTTP-инфраструктуру:**

| Адаптер                    | Базовый класс                    | HTTP-клиент              | Примечание                                                                           |
| -------------------------- | -------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ |
| **ChemblAdapter**          | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, 14 entities, 3 req/sec. Native pagination and filtering (without mixins) |
| **UniProtAdapter**         | `BaseHttpAdapter`                | `UnifiedHTTPClient`      | Async HTTP, 100 req/sec. Mixin: `PaginatedFetcherMixin`                              |
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

Реализует `StoragePort` для работы с различными уровнями данных (Bronze, Silver, Gold).

Реализация разделена на три writer-а, каждый декомпозирован на mixins:

- **`BronzeWriter`** (`bronze_writer.py`): Запись сырых данных в формате JSONL + zstd. Atomic writes через temp file + rename, генерация checksums.
- **`SilverWriter`** (`silver_writer.py`): Запись в Delta Lake таблицы с наследованием от `BaseDeltaWriter`, ACID-транзакциями, логикой merge/upsert для идемпотентности, поддержкой Time Travel и 7-дневным VACUUM retention.
- **`GoldWriter`** (`gold_writer.py`): Запись бизнес-готовых данных с наследованием от `BaseDeltaWriter`, строгой валидацией через Pandera, поддержкой SCD Type 2 и контрактов данных.

#### 2.2.1. BronzeWriter Mixin Decomposition

| Файл                              | Назначение                                    |
| --------------------------------- | --------------------------------------------- |
| `bronze_writer.py`                | Главный `BronzeWriter`                        |
| `bronze_writer_io_mixin.py`       | I/O операции (JSONL write, compression)       |
| `bronze_writer_metadata_mixin.py` | Генерация Bronze metadata sidecar             |
| `bronze_writer_metrics_mixin.py`  | Метрики Bronze write операций                 |
| `bronze_writer_side_effects_mixin.py` | Side effects (checksum, notifications)    |
| `bronze_writer_validation_mixin.py`| Валидация входных данных                     |
| `bronze_write_result_helpers.py`  | Helper functions для write result              |

#### 2.2.2. SilverWriter Mixin Decomposition

| Файл                                    | Назначение                                    |
| ---------------------------------------- | --------------------------------------------- |
| `silver_writer.py`                       | Главный `SilverWriter`                        |
| `silver_writer_arrow_mixin.py`           | PyArrow conversion и schema alignment         |
| `silver_writer_delta_mixin.py`           | Delta Lake write/merge operations             |
| `silver_writer_merged_mixin.py`          | Post-merge reconciliation                     |
| `silver_writer_metadata_mixin.py`        | Silver metadata sidecar generation            |
| `silver_writer_postwrite_mixin.py`       | Post-write operations (VACUUM, stats)         |
| `silver_writer_validation_mixin.py`      | Schema validation и data quality              |
| `silver_writer_maintenance_mixin.py`     | Maintenance operations (OPTIMIZE, Z-ORDER)    |
| `silver_writer_delta_helpers.py`         | Delta Lake helper functions                   |
| `silver_writer_merge_resilience_helpers.py` | Merge retry и resilience logic             |
| `silver_writer_pipeline_helpers.py`      | Pipeline-specific helpers                     |
| `silver_writer_runtime_helpers.py`       | Runtime configuration helpers                 |

#### 2.2.3. GoldWriter Mixin Decomposition

| Файл                              | Назначение                                    |
| --------------------------------- | --------------------------------------------- |
| `gold_writer.py`                  | Главный `GoldWriter`                          |
| `gold_writer_io_mixin.py`         | I/O operations (Delta write)                  |
| `gold_writer_io_delta_mixins.py`  | Delta-specific I/O (merge, overwrite)         |
| `gold_writer_metadata_mixin.py`   | Gold metadata sidecar generation              |
| `gold_writer_validation_mixin.py` | Pandera schema validation                     |
| `gold_writer_read_cleanup_mixin.py`| Read и cleanup operations                    |
| `gold_writer_io_helpers.py`       | I/O helper functions                          |
| `gold_writer_metadata_audit.py`   | Metadata audit trail                          |
| `gold_writer_pipeline_helpers.py` | Pipeline-specific helpers                     |

#### 2.2.4. Storage Support

**Delta Lake infrastructure:**

| Файл                     | Компонент            | Назначение                                    |
| ------------------------ | -------------------- | --------------------------------------------- |
| `base_delta_writer.py`   | `BaseDeltaWriter`    | Базовый класс для Silver/Gold writers         |
| `delta_writer.py`        | `DeltaWriter`        | Low-level Delta Lake write adapter            |
| `delta_reader.py`        | `DeltaReader`        | Чтение Delta Lake таблиц                      |
| `arrow_converter.py`     | `ArrowDataConverter` | PyArrow conversion utilities                  |
| `_atomic.py`             | `atomic_write_text`  | Atomic file write (temp + rename)             |

**Metadata infrastructure:**

| Файл                                  | Компонент          | Назначение                                    |
| -------------------------------------- | ------------------ | --------------------------------------------- |
| `metadata_writer.py`                  | `MetadataWriter`   | Запись metadata sidecar YAML                  |
| `metadata_writer_operations.py`       | Internal operations| Подготовка, telemetry, retry для metadata     |
| `metadata_builder.py`                 | `MetadataBuilder`  | Сборка metadata моделей                       |
| `metadata_builder_base.py`            | Base builder       | Базовые функции сборки metadata               |
| `metadata_builder_composite_helpers.py`| Composite helpers | Metadata для composite pipelines              |

**Other storage:**

| Файл                           | Компонент                  | Назначение                              |
| ------------------------------ | -------------------------- | --------------------------------------- |
| `retention_manager.py`         | `RetentionPolicy`          | VACUUM retention и Delta maintenance    |
| `composite_checkpoint_writer.py`| `CompositeCheckpointWriter`| Запись composite checkpoint             |

#### 2.1.2. Adapter Support Infrastructure

**Error handling:**

| Файл                         | Компонент                   | Назначение                                    |
| ---------------------------- | --------------------------- | --------------------------------------------- |
| `_error_classifier.py`       | Internal error classifier   | Внутренняя классификация ошибок               |
| `adapter_error_classifier.py`| `AdapterErrorClassifier`    | Классификация ошибок адаптеров (retryable и др.) |
| `adapter_error_mapper.py`    | `AdapterErrorMapper`        | Маппинг HTTP-ошибок на domain exceptions      |
| `error_handling.py`          | Error handling utilities    | Общие утилиты обработки ошибок                |

**Health monitoring:**

| Файл                      | Компонент                | Назначение                                    |
| ------------------------- | ------------------------ | --------------------------------------------- |
| `health_check_mixin.py`   | `HealthCheckMixin`       | Mixin для реализации `health_check()` в адаптерах |
| `health_check_contract.py`| `HealthCheckContract`    | Контракт health check response                |
| `health_probe_policy.py`  | `HealthProbePolicy`      | Политика health probes (interval, timeout)    |
| `health_status_policy.py` | `HealthStatusPolicy`     | Политика определения статуса по результатам   |

**Base classes and mixins:**

| Файл                        | Компонент              | Назначение                                    |
| --------------------------- | ---------------------- | --------------------------------------------- |
| `base.py`                   | `BaseHttpAdapter`      | Базовый класс для async HTTP адаптеров        |
| `sync_base.py`              | `BaseSyncAdapter`      | Базовый класс для sync адаптеров (pubchempy)  |
| `base_metrics.py`           | Adapter metrics        | Метрики адаптеров (requests, latency)         |
| `filterable_mixin.py`       | `FilterableMixin`      | Mixin для фильтрации по ID-спискам            |
| `cached_bronze_data_source.py` | `CachedBronzeDataSource` | Кеширование Bronze данных               |
| `validation.py`             | Validation utilities   | Валидация параметров адаптеров                |

**Subpackages:** `http/` (UnifiedHTTPClient, rate limiter, circuit breaker), `common/` (shared adapter utilities), `input/` (input data sources), `decorators/` (adapter decorators).

### 2.3. `locking/` — Реализация Блокировок

**Расположение:** `src/bioetl/infrastructure/locking/`

Содержит реализацию `LockPort` для координации пайплайнов.

**Текущая реализация (Local-Only):**

- **`MemoryLock`**: In-memory блокировка для локального развёртывания
- Однопроцессная изоляция (не распределённая)
- Поддержка exclusive-режима для backfill/rebuild

> **Note:** Redis-блокировки (ADR-003) superseded в пользу local-only стратегии.
> См. [ADR-010](decisions/ADR-010-local-only-deployment.md) для обоснования.

**Расширяемость:** Порт `LockPort` остаётся неизменным — при необходимости можно добавить
Redis-адаптер без изменения domain/application слоёв.

### 2.4. `checkpoint/` и `quarantine/`

- **`checkpoint/`**: Реализация `CheckpointPort` для сохранения состояния пайплайнов. Текущая реализация использует локальную файловую систему (`LocalCheckpoint`). См. [ADR-010](decisions/ADR-010-local-only-deployment.md).
- **`quarantine/`**: Реализация `QuarantinePort` для записи "плохих" данных в отдельное хранилище для последующего анализа.

### 2.5. `observability/` — Наблюдаемость

**Расположение:** `src/bioetl/infrastructure/observability/`

Содержит реализацию `MetricsPort` (например, с использованием библиотеки Prometheus Client) и настройку логирования (например, `structlog`).

## 3. Принципы Работы

- **Запрет на бизнес-логику:** В этом слое не должно быть бизнес-правил. Его задача — получить данные "как есть" или записать их "как сказано".
- **Инверсия зависимостей:** Классы из `Infrastructure` зависят от абстракций (`Protocol`) из `Domain`, а не наоборот. Это позволяет подменять реализации без изменения ядра системы.
- **Конфигурация:** Все необходимые параметры (API-ключи, пути, адреса серверов) адаптеры получают через DI из конфигурационных объектов.

----------------------------------------------------------------------

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                                 | Текущий            | Следующий →                                |
| -------------------------------------------- | ------------------ | ------------------------------------------ |
| [Application Layer](02-application-layer.md) | **Infrastructure** | [Interfaces Layer](04-interfaces-layer.md) |

### Связанные Диаграммы

| Диаграмма              | Файл                                                                                                            | Описание                                         |
| ---------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Infrastructure Classes | [10-infrastructure-layer-class-diagram.mmd](mmd-diagrams/foundation/10-infrastructure-layer-class-diagram.mmd) | Классы слоя Infrastructure                       |
| Provider Adapters      | [30-port-adapter-mapping.mmd](mmd-diagrams/foundation/30-port-adapter-mapping.mmd)                                  | Обзор 7 провайдеров и их rate limits             |
| HTTP Infrastructure    | [10-infrastructure-layer-class-diagram.mmd](mmd-diagrams/foundation/10-infrastructure-layer-class-diagram.mmd) | UnifiedHTTPClient, Rate Limiter, Circuit Breaker |
| Circuit Breaker        | [07-circuit-breaker-states.mmd](mmd-diagrams/foundation/07-circuit-breaker-states.mmd)                         | Состояния Circuit Breaker                        |
| Storage Architecture   | [19-delta-lake-write-sequence.mmd](mmd-diagrams/foundation/19-delta-lake-write-sequence.mmd)                    | Bronze, Silver, Gold writers                     |
| MemoryLock             | [16-memory-lock-class.mmd](mmd-diagrams/foundation/16-memory-lock-class.mmd)                                   | Класс MemoryLock                                 |

### Связанные ADR

| ADR                                                            | Тема                           |
| -------------------------------------------------------------- | ------------------------------ |
| [ADR-003](decisions/ADR-003-in-memory-locking-strategy.md)     | In-Memory Locking Strategy     |
| [ADR-007](decisions/ADR-007-circuit-breaker-implementation.md) | Circuit Breaker Implementation |
| [ADR-010](decisions/ADR-010-local-only-deployment.md)          | Local-Only Deployment          |
| [ADR-017](decisions/ADR-017-observability-architecture.md)     | Observability Architecture     |

### Смежные Разделы Документации

- [Domain Layer](01-domain-layer.md) — порты, реализуемые адаптерами
- [Composition Layer](05-composition-layer.md) — фабрики создания адаптеров
- [API Reference: Infrastructure](../04-reference/api/infrastructure.md) — API документация слоя
- [RULES.md §3 "Ошибки"](../00-project/RULES.md) — классификация ошибок, retry logic
