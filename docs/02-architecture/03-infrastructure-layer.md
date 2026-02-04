# Слой Infrastructure (Инфраструктура)

**Расположение:** `src/bioetl/infrastructure/`

## 1. Назначение

Слой `Infrastructure` содержит конкретные реализации **портов**, определённых в слое `Domain`. Он отвечает за всё взаимодействие с внешним миром: базы данных, файловые системы, сетевые API, брокеры сообщений и т.д.

Этот слой является "мостом" между чистой бизнес-логикой и реальными технологиями.

**Ключевые характеристики:**
- **Реализация портов:** Классы в этом слое реализуют `Protocol` из `domain.ports`.
- **Зависимости:** Здесь находятся все "грязные" детали: HTTP-клиенты, коннекторы к БД, специфичные SDK.
- **Изменчивость:** Этот слой наиболее подвержен изменениям при смене технологий (например, переход с локальной ФС на объектное хранилище в будущем).

## 2. Ключевые Компоненты

### 2.1. `adapters/` — Адаптеры к Внешним API

**Расположение:** `src/bioetl/infrastructure/adapters/`

Содержит адаптеры для конкретных источников данных (ChEMBL, PubChem, UniProt и т.д.). Каждый адаптер — это класс, реализующий `DataSourcePort`.

Создание и настройка адаптеров централизованы в [DataSourceRegistry](05-composition-layer.md#22-factories-фабрики-компонентов) слоя Composition.

**Обязанности адаптера:**
- Управление HTTP-соединениями через `UnifiedHTTPClient`.
- Обработка специфичных для API ошибок (например, `429 Rate Limit`).
- Преобразование ответа API в стандартизированный формат (словари Python).
- Реализация `health_check()` для проверки доступности API.

#### 2.1.1. Унифицированный HTTP-клиент

**Все адаптеры используют унифицированную HTTP-инфраструктуру:**

| Адаптер | Базовый класс | HTTP-клиент | Примечание |
|---------|---------------|-------------|------------|
| **ChemblAdapter** | `BaseHttpAdapter` | `UnifiedHTTPClient` | Async HTTP, 13 entities |
| **UniProtAdapter** | `BaseHttpAdapter` | `UnifiedHTTPClient` | Async HTTP, 100 req/sec |
| **PubMedAdapter** | `@dataclass` | `UnifiedHTTPClient` | Async HTTP, 3 req/sec |
| **PubChemAdapter** | `BaseSyncAdapter` | `pubchempy` + ThreadPool | Legacy sync, 5 req/sec |
| **CrossRefAdapter** | `BaseHttpAdapter` | `UnifiedHTTPClient` | Async HTTP, polite pool |
| **OpenAlexAdapter** | `BaseHttpAdapter` | `UnifiedHTTPClient` | Async HTTP, 10 req/sec |
| **SemanticScholarAdapter** | `BaseHttpAdapter` | `UnifiedHTTPClient` | Async HTTP, 100 req/5min |

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
- **Rate Limiter** (`TokenBucket`): Ограничение частоты запросов
- **Circuit Breaker**: Защита от каскадных отказов
- **Retry Logic**: Автоматические повторы с exponential backoff
- **Metrics**: Интеграция с `MetricsPort` для наблюдаемости

**Для sync-библиотек** (pubchempy, biopython) используется `BaseSyncAdapter`:
- `ThreadPoolExecutor` для изоляции блокирующего I/O
- Собственные `TokenBucket` и `CircuitBreaker`
- Async-обёртка через `run_in_executor()`

### 2.2. `storage/` — Адаптеры Хранилищ

**Расположение:** `src/bioetl/infrastructure/storage/`

Реализует `StoragePort` для работы с различными уровнями данных (Bronze, Silver, Gold).

- **`BronzeStorageAdapter`**: Отвечает за запись сырых данных (JSONL) в файловое хранилище (например, локальный диск; объектное хранилище — только в future-режиме).
- **`SilverStorageAdapter`**: Управляет записью в Delta Lake таблицы, реализуя логику `merge` (upsert) для обеспечения идемпотентности.
- **`GoldStorageAdapter`**: Записывает агрегированные витрины данных.

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

---

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий | Текущий | Следующий → |
|--------------|---------|-------------|
| [Application Layer](02-application-layer.md) | **Infrastructure** | [Interfaces Layer](04-interfaces-layer.md) |

### Связанные Диаграммы

| Диаграмма | Файл | Описание |
|-----------|------|----------|
| Infrastructure Classes | [10-infrastructure-layer-class-diagram.mermaid](diagrams/10-infrastructure-layer-class-diagram.mermaid) | Классы слоя Infrastructure |
| Provider Adapters | [../diagrams/mermaid/23_provider_adapters_overview.mmd](../diagrams/mermaid/23_provider_adapters_overview.mmd) | Обзор 7 провайдеров и их rate limits |
| HTTP Infrastructure | [../diagrams/mermaid/14_http_infrastructure.mmd](../diagrams/mermaid/14_http_infrastructure.mmd) | UnifiedHTTPClient, Rate Limiter, Circuit Breaker |
| Circuit Breaker | [07-circuit-breaker-states.mermaid](diagrams/07-circuit-breaker-states.mermaid) | Состояния Circuit Breaker |
| Storage Architecture | [../diagrams/mermaid/13_storage_architecture.mmd](../diagrams/mermaid/13_storage_architecture.mmd) | Bronze, Silver, Gold writers |
| MemoryLock | [16-memory-lock-class.mermaid](diagrams/16-memory-lock-class.mermaid) | Класс MemoryLock |

### Связанные ADR

| ADR | Тема |
|-----|------|
| [ADR-003](decisions/ADR-003-in-memory-locking-strategy.md) | In-Memory Locking Strategy |
| [ADR-007](decisions/ADR-007-circuit-breaker-implementation.md) | Circuit Breaker Implementation |
| [ADR-010](decisions/ADR-010-local-only-deployment.md) | Local-Only Deployment |
| [ADR-017](decisions/ADR-017-observability-architecture.md) | Observability Architecture |

### Смежные Разделы Документации

- [Domain Layer](01-domain-layer.md) — порты, реализуемые адаптерами
- [Composition Layer](05-composition-layer.md) — фабрики создания адаптеров
- [API Reference: Infrastructure](../04-reference/api/infrastructure.md) — API документация слоя
- [RULES.md §3 "Ошибки"](../RULES.md) — классификация ошибок, retry logic
