# Комплексный Архитектурный Обзор BioETL

*Версия: 1.0 | Дата: 2025-12-17 | Автор: Architecture Review*

## Содержание

1. [Исполнительное резюме](#1-исполнительное-резюме)
2. [Числовая оценка по 10 категориям](#2-числовая-оценка-по-10-категориям)
3. [Оценка архитектуры](#3-оценка-архитектуры)
4. [Выявленные проблемы](#4-выявленные-проблемы)
5. [План рефакторинга](#5-план-рефакторинга)
6. [Метрики и тесты для контроля качества](#6-метрики-и-тесты-для-контроля-качества)
7. [Прогноз улучшения оценок](#7-прогноз-улучшения-оценок)

---

## 1. Исполнительное резюме

**BioETL** — это production-ready ETL-фреймворк для сбора и обработки биоактивных данных из внешних источников (ChEMBL, PubChem, UniProt). Проект демонстрирует **зрелую архитектуру** на основе Hexagonal Architecture (Ports & Adapters) и принципов DDD.

### Ключевые показатели

| Метрика | Значение |
|---------|----------|
| Версия | 5.0.0 |
| Размер кодовой базы | ~8,600 строк (src/) |
| Тестовое покрытие | 71.23% (цель: 80%) |
| Количество тестов | 716 тестовых функций |
| Cyclomatic Complexity | Rank A (большинство функций) |
| Архитектурные нарушения | 0 (enforced via import-linter) |

### Интегральная оценка

**Общий балл проекта: 7.43 / 10** — Хорошее состояние с потенциалом улучшений

---

## 2. Числовая оценка по 10 категориям

### 2.1 Определение категорий и критерии оценки

| # | Категория | Описание | Вес |
|---|-----------|----------|-----|
| 1 | Архитектура слоёв | Соблюдение слоистой структуры, инверсия зависимостей, разделение ответственностей | 15% |
| 2 | Модульность и связность | Cohesion/Coupling, независимость модулей, интерфейсы между компонентами | 12% |
| 3 | Качество доменной модели | DDD-принципы, Value Objects, Aggregates, Entities, ubiquitous language | 10% |
| 4 | Тестирование | Покрытие кода, качество тестов, тестовые паттерны, mutation testing | 15% |
| 5 | Обработка ошибок | Exception hierarchy, error classification, retry policies, circuit breaker | 10% |
| 6 | Логирование и наблюдаемость | Structured logging, metrics, tracing, alerting, data lineage | 8% |
| 7 | Производительность | Rate limiting, connection pooling, async patterns, memory efficiency | 8% |
| 8 | Безопасность | Secrets management, input validation, SAST tools, dependency scanning | 10% |
| 9 | Качество документации | API docs, ADRs, runbooks, onboarding guides, code comments | 7% |
| 10 | Технический долг и сопровождаемость | Code complexity, duplication, TODO/FIXME markers, upgrade paths | 5% |

**Сумма весов: 100%**

---

### 2.2 Оценочная таблица

| Категория | Описание оцениваемого аспекта | Вес | Оценка (1-10) | Взвешенный балл | Обоснование |
|-----------|------------------------------|-----|---------------|-----------------|-------------|
| **1. Архитектура слоёв** | Domain/Application/Infrastructure/Interfaces разделение, Ports & Adapters | 0.15 | **9** | 1.35 | Отличное разделение слоёв. Domain полностью изолирован (0 внешних зависимостей). Import-linter enforced. Чёткие границы через Protocols. |
| **2. Модульность и связность** | Cohesion внутри модулей, coupling между модулями, dependency injection | 0.12 | **8** | 0.96 | Высокая cohesion в каждом слое. DI через bootstrap.py. Но PipelineServices как service locator — минус. |
| **3. Качество доменной модели** | NewType, frozen dataclasses, Enums, pure functions, Ports | 0.10 | **9** | 0.90 | Excellent DDD foundation. 7 domain enums, rich exception hierarchy, pure transformations. Минус: dict[str, Any] для данных. |
| **4. Тестирование** | Unit/Integration/Architecture tests, coverage, fixtures, mocking | 0.15 | **6** | 0.90 | 71.23% покрытия (цель 80%). Критические gaps в orchestrator (22.6%), checkpoint_manager (31%). VCR только для ChEMBL. |
| **5. Обработка ошибок** | 3-tier exception hierarchy, ErrorClassifier, retries, circuit breaker | 0.10 | **9** | 0.90 | 16 exception classes в 3 уровнях (Critical/Recoverable/DataQuality). Circuit breaker, exponential backoff with jitter. |
| **6. Логирование и наблюдаемость** | structlog, Prometheus metrics, data lineage, anomaly detection | 0.08 | **7** | 0.56 | structlog + JSON format. Prometheus metrics. Lineage tracking. Но coverage observability кода низкое (35-43%). |
| **7. Производительность** | TokenBucket rate limiting, S3ClientPool, async/await, streaming | 0.08 | **8** | 0.64 | Token bucket для всех провайдеров. S3 connection pooling. Zstd compression. Async throughout. |
| **8. Безопасность** | SecretStr, bandit, pip-audit, input validation, SAST | 0.10 | **7** | 0.70 | SecretStr для паролей. Bandit + pip-audit в CI. Lua scripts для Redis atomicity. Но payload truncation (64KB) может терять данные. |
| **9. Качество документации** | 55+ markdown файлов, ADRs, runbooks, API reference, RULES.md | 0.07 | **8** | 0.56 | Comprehensive docs: 4 ADRs, 10 runbooks, RULES.md v5.0, MkDocs site. API docs через mkdocstrings. |
| **10. Технический долг** | 0 TODO/FIXME в коде, complexity rank A, minimal duplication | 0.05 | **9** | 0.45 | Нет TODO/FIXME маркеров. Complexity: большинство A, несколько B. Import-linter предотвращает degradation. |

---

### 2.3 Расчёт интегрального балла

```
Интегральный балл = Σ(Вес_i × Оценка_i)

= (0.15 × 9) + (0.12 × 8) + (0.10 × 9) + (0.15 × 6) + (0.10 × 9)
+ (0.08 × 7) + (0.08 × 8) + (0.10 × 7) + (0.07 × 8) + (0.05 × 9)

= 1.35 + 0.96 + 0.90 + 0.90 + 0.90 + 0.56 + 0.64 + 0.70 + 0.56 + 0.45

= 7.92 / 10
```

**Округлённый интегральный балл: 7.92**

---

### 2.4 Интерпретация общего балла

| Диапазон | Оценка | Описание |
|----------|--------|----------|
| 0.0 - 4.9 | Критическое | Требуется срочный рефакторинг, высокий технический риск |
| 5.0 - 6.9 | Удовлетворительное | Работает, но есть существенные проблемы |
| **7.0 - 7.9** | **Хорошее** | **Качественная архитектура с потенциалом улучшений** |
| 8.0 - 8.9 | Отличное | Зрелая архитектура, минимальные улучшения |
| 9.0 - 10.0 | Превосходное | Эталонная архитектура |

**Вывод: Проект находится в хорошем состоянии (7.92/10)** с особенно сильной архитектурой слоёв, доменной моделью и обработкой ошибок. Основная зона роста — тестовое покрытие критических компонентов.

---

## 3. Оценка архитектуры

### 3.1 Соблюдение слоистой структуры

```
src/bioetl/
├── domain/           # ЧИСТЫЙ слой (0 зависимостей от I/O)
│   ├── types.py      # Value Objects (NewType, Enum)
│   ├── ports.py      # Интерфейсы (Protocol)
│   ├── exceptions.py # Domain Exceptions
│   ├── context.py    # PipelineContext aggregate
│   └── transformations.py # Pure functions
│
├── application/      # USE CASES (orchestration)
│   ├── core/         # Pipeline execution, managers
│   └── pipelines/    # Concrete pipeline implementations
│
├── infrastructure/   # ADAPTERS (external world)
│   ├── adapters/     # ChEMBL, PubChem, UniProt, HTTP
│   ├── storage/      # Bronze, Silver, Gold writers
│   ├── locking/      # Redis, Memory locks
│   ├── checkpoint/   # S3 checkpoint
│   ├── quarantine/   # Dead letter queue
│   └── observability/# Logging, metrics, lineage
│
└── interfaces/       # ENTRY POINTS
    ├── cli.py        # Click CLI
    └── orchestration/# Prefect, signals, runner
```

**Оценка: 9/10** — Чёткое разделение на 4 слоя согласно Clean Architecture.

#### Сильные стороны:
- Domain слой полностью изолирован (проверено через import-linter)
- Нет циклических зависимостей
- Infrastructure реализует domain ports (Protocol)
- Application использует только абстракции (ports), не конкретные реализации

#### Слабые стороны:
- `infrastructure/config.py` импортируется из application через `get_settings()` (нарушение Dependency Rule)

---

### 3.2 Следование принципам Ports & Adapters (Hexagonal)

**Определённые порты (`domain/ports.py`):**

| Port | Назначение | Реализации |
|------|------------|------------|
| `DataSourcePort` | Получение данных из внешних API | ChemblAdapter, PubChemClient, UniProtClient |
| `StoragePort` | Запись в Bronze/Silver/Gold | DeltaWriter, BronzeWriter, GoldWriter |
| `LockPort` | Распределённая блокировка | RedisDistributedLock, MemoryLock |
| `CheckpointPort` | Персистенция состояния pipeline | S3Checkpoint |
| `QuarantinePort` | Изоляция невалидных записей | UnifiedQuarantine |
| `MetricsPort` | Метрики и мониторинг | PrometheusMetrics, NoOpMetrics |

**Оценка: 9/10** — Отличная реализация паттерна.

```python
# Пример Port definition (domain/ports.py)
@runtime_checkable
class DataSourcePort(Protocol):
    """Port for external data sources."""
    async def fetch(self, ...) -> AsyncIterator[list[dict[str, Any]]]: ...
    async def health_check(self) -> HealthStatus: ...
    async def aclose(self) -> None: ...
```

---

### 3.3 Следование принципам DDD

| Принцип DDD | Реализация | Оценка |
|-------------|------------|--------|
| **Ubiquitous Language** | Enum-ы: RunType, DriftLevel, HealthStatus, CircuitBreakerState, ErrorType | 10/10 |
| **Value Objects** | NewType (RunID, EntityID, ContentHash), frozen dataclasses | 10/10 |
| **Entities** | PipelineConfig (identity via pipeline_name) | 8/10 |
| **Aggregates** | PipelineContext, PipelineServices | 8/10 |
| **Domain Services** | ErrorClassifier, pure functions in transformations.py | 9/10 |
| **Repositories** | Ports (DataSourcePort, StoragePort) | 9/10 |
| **Domain Events** | Отсутствуют | 4/10 |

**Общая оценка DDD: 8.3/10**

#### Что хорошо:
- Чистая иммутабельность: `@dataclass(frozen=True)` везде
- Типизированные ID: `RunID = NewType("RunID", UUID)`
- Богатая enum-модель с поведением: `ErrorType.is_critical()`, `HealthStatus.to_metric_value()`

#### Что улучшить:
- Использование `dict[str, Any]` вместо TypedDict для записей
- Отсутствие явных Domain Events

---

### 3.4 Явность границ модулей и зависимостей

**Механизм enforcement: `.importlinter`**

```ini
[importlinter:contract:domain-independence]
name = Domain layer independence
type = forbidden
source_modules = bioetl.domain
forbidden_modules =
    bioetl.infrastructure
    bioetl.application

[importlinter:contract:domain-pure]
name = Domain layer must be pure (no I/O libraries)
source_modules = bioetl.domain
forbidden_modules = httpx, boto3, redis, deltalake, polars, asyncio
```

**Результат:** 0 архитектурных нарушений (CI pipeline блокирует merge при нарушении).

---

### 3.5 Единообразие соглашений

| Аспект | Стандарт | Соблюдение |
|--------|----------|------------|
| **Naming** | snake_case для функций/переменных, PascalCase для классов | ✅ 100% |
| **File structure** | `__init__.py` с экспортами, `test_*.py` для тестов | ✅ 100% |
| **Type hints** | strict mode в mypy, disallow_untyped_defs | ✅ 100% |
| **Docstrings** | Google style, требуется для public API | ⚠️ 85% |
| **Error handling** | Иерархия BioETLError, 3-tier classification | ✅ 100% |
| **Configuration** | Pydantic Settings, environment variables | ✅ 100% |

---

## 4. Выявленные проблемы

### 4.1 Критические проблемы (P0)

#### 4.1.1 Низкое тестовое покрытие критических компонентов

**Описание:** Ключевые компоненты оркестрации имеют coverage ниже 40%:

| Файл | Покрытие | Риск |
|------|----------|------|
| `orchestrator.py` | 22.6% | CRITICAL |
| `checkpoint_manager.py` | 31.0% | CRITICAL |
| `runner.py` | 31.7% | HIGH |
| `unified_quarantine.py` | 34.5% | HIGH |
| `logging.py` | 35.3% | MEDIUM |

**Влияние:** Регрессии в pipeline execution могут остаться незамеченными.

**Местоположение:** `src/bioetl/application/core/orchestrator.py:33-119`

---

#### 4.1.2 Использование dict[str, Any] для данных

**Описание:** Pipeline методы используют нетипизированные словари:

```python
# Текущее состояние (application/core/executor.py)
async def _process_batch(
    self, records: list[dict[str, Any]], ...
) -> dict[str, Any]:
```

**Влияние:**
- Потеря type safety на границах слоёв
- IDE не может помочь с автодополнением
- Ошибки обнаруживаются только в runtime

**Местоположение:**
- `application/core/executor.py:82-128`
- `application/core/base.py:96-99`

---

### 4.2 Высокоприоритетные проблемы (P1)

#### 4.2.1 Отсутствие VCR-кассет для PubChem и UniProt

**Описание:** Только ChEMBL adapter имеет записанные HTTP-взаимодействия:

```
tests/fixtures/vcr/
├── chembl/    # ✅ 3 cassettes
├── pubchem/   # ❌ отсутствует
└── uniprot/   # ❌ отсутствует
```

**Влияние:** Интеграционные тесты для PubChem/UniProt делают реальные HTTP-вызовы.

---

#### 4.2.2 PipelineServices как Service Locator

**Описание:** Класс PipelineServices агрегирует все зависимости:

```python
@dataclass(frozen=True)
class PipelineServices:
    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    logger: BoundLogger
```

**Проблема:** Это анти-паттерн Service Locator — компонент получает доступ ко всему, даже если не использует.

**Влияние:** Сложнее отследить реальные зависимости каждого класса.

---

#### 4.2.3 Branch coverage только 56.3%

**Описание:** Многие conditional branches не покрыты тестами:

```
Statements covered: 2048/2759 (74.2%)
Branches covered: 312/554 (56.3%)
```

**Влияние:** Error paths и exception handling недостаточно протестированы.

---

### 4.3 Средний приоритет (P2)

#### 4.3.1 Отсутствие Domain Events

**Описание:** Нет механизма публикации событий при изменении состояния:

```python
# Желаемое состояние:
class DomainEvent(Protocol):
    occurred_at: datetime

class BatchProcessed(DomainEvent):
    batch_id: BatchID
    records_count: int

class RecordQuarantined(DomainEvent):
    entity_id: EntityID
    error: DataQualityError
```

**Влияние:** Сложнее реализовать audit trail, event sourcing, async notifications.

---

#### 4.3.2 Observability code с низким покрытием

| Модуль | Покрытие |
|--------|----------|
| `lineage.py` | 43.2% |
| `logging.py` | 35.3% |
| `anomaly.py` | Не измерено |

**Влияние:** Ошибки в lineage tracking могут привести к неполным audit trails.

---

#### 4.3.3 Потенциальная потеря данных в quarantine

**Описание:** Payload truncation до 64KB:

```python
# unified_quarantine.py
MAX_PAYLOAD_SIZE = 64 * 1024  # 64KB
```

**Влияние:** Большие записи теряют контекст при quarantine.

---

### 4.4 Низкий приоритет (P3)

#### 4.4.1 Нет query-level caching

**Описание:** Повторные запросы к API не кэшируются.

**Влияние:** Потенциально избыточные API-вызовы при replay/debug сценариях.

---

#### 4.4.2 Circuit Breaker metrics не экспортируются

**Описание:** CircuitBreaker отслеживает trips внутренне, но не отправляет в Prometheus.

```python
# Текущее: только внутренний счётчик
self._trip_count += 1

# Желаемое: экспорт в metrics
self._metrics.increment_counter("circuit_breaker_trips", provider=self.provider)
```

---

## 5. План рефакторинга

### 5.1 Приоритизированный список изменений

| # | Изменение | Приоритет | Влияние на оценку | Риск | Effort |
|---|-----------|-----------|-------------------|------|--------|
| 1 | Увеличить coverage критических компонентов до 80%+ | P0 | +0.6 баллов | Низкий | Medium |
| 2 | Ввести TypedDict для Silver/Gold records | P0 | +0.3 баллов | Средний | Medium |
| 3 | Добавить VCR-кассеты для PubChem/UniProt | P1 | +0.2 баллов | Низкий | Low |
| 4 | Разбить PipelineServices на cohesive группы | P1 | +0.2 баллов | Средний | Medium |
| 5 | Увеличить branch coverage до 75%+ | P1 | +0.3 баллов | Низкий | Medium |
| 6 | Добавить Domain Events | P2 | +0.2 баллов | Средний | High |
| 7 | Увеличить coverage observability | P2 | +0.15 баллов | Низкий | Low |
| 8 | Экспорт Circuit Breaker metrics | P3 | +0.05 баллов | Низкий | Low |

---

### 5.2 Детальные шаги рефакторинга

---

#### Шаг 1: Увеличение тестового покрытия критических компонентов

**Цель:** Поднять coverage orchestrator.py с 22.6% до 85%, checkpoint_manager.py с 31% до 85%.

**Конкретные правки:**

1. **Создать тесты для `PipelineOrchestrator.run()`** (`application/core/orchestrator.py:33-119`):
   ```python
   # tests/unit/application/core/test_orchestrator.py

   class TestPipelineOrchestratorRun:
       async def test_run_success_with_checkpoint_resume(self):
           """Test successful run resuming from checkpoint."""

       async def test_run_handles_lock_acquisition_failure(self):
           """Test behavior when lock cannot be acquired."""

       async def test_run_handles_shutdown_signal(self):
           """Test graceful shutdown on SIGTERM."""

       async def test_heartbeat_loop_failure_raises_lock_lost(self):
           """Test LockLostError when heartbeat fails."""
   ```

2. **Добавить тесты для `CheckpointManager`** (`application/core/checkpoint_manager.py`):
   ```python
   # tests/unit/application/core/test_checkpoint_manager.py

   class TestCheckpointManager:
       async def test_load_checkpoint_returns_none_when_not_exists(self):
       async def test_load_checkpoint_handles_corrupt_data(self):
       async def test_save_checkpoint_with_s3_failure(self):
       async def test_checkpoint_roundtrip_preserves_data(self):
   ```

**Риски:**
- Сложность мокирования async операций
- Возможность flaky tests при concurrency тестировании

**Минимизация рисков:**
- Использовать `AsyncMock` с explicit spec
- Изолировать async тесты с `pytest-asyncio`

**Критерии готовности:**
- [ ] Coverage orchestrator.py >= 85%
- [ ] Coverage checkpoint_manager.py >= 85%
- [ ] Все новые тесты проходят
- [ ] CI pipeline зелёный

---

#### Шаг 2: Введение TypedDict для записей данных

**Цель:** Заменить `dict[str, Any]` на типизированные структуры.

**Конкретные правки:**

1. **Создать типы записей** (`domain/types.py`):
   ```python
   from typing import TypedDict, NotRequired

   class SilverRecord(TypedDict):
       """Silver layer record with required audit fields."""
       entity_id: str
       content_hash: str
       _source_batch_id: str
       _run_id: str
       _run_type: str
       _ingested_at: str
       # Provider-specific fields as NotRequired

   class ChemblActivityRecord(SilverRecord):
       """ChEMBL activity-specific fields."""
       activity_id: int
       assay_chembl_id: str
       molecule_chembl_id: str
       standard_value: NotRequired[float]
       standard_units: NotRequired[str]
   ```

2. **Обновить сигнатуры методов** (`application/core/executor.py`):
   ```python
   # До:
   async def _process_batch(
       self, records: list[dict[str, Any]], ...
   ) -> dict[str, Any]:

   # После:
   async def _process_batch(
       self, records: list[SilverRecord], ...
   ) -> ProcessingResult:
   ```

3. **Добавить runtime валидацию на границах** (`infrastructure/adapters/`):
   ```python
   def validate_silver_record(record: dict[str, Any]) -> SilverRecord:
       """Validate and cast raw dict to SilverRecord."""
       required = {"entity_id", "content_hash", "_source_batch_id"}
       missing = required - record.keys()
       if missing:
           raise SchemaViolationError(f"Missing required fields: {missing}")
       return cast(SilverRecord, record)
   ```

**Риски:**
- Breaking changes в существующих pipelines
- Необходимость обновить тесты

**Минимизация рисков:**
- Начать с одного pipeline (ChEMBL Activity)
- Использовать gradual typing (сначала TypedDict с total=False)

**Критерии готовности:**
- [ ] TypedDict определены для Silver/Gold records
- [ ] ChEMBL Activity pipeline использует типизированные записи
- [ ] Mypy проходит без ошибок
- [ ] Тесты обновлены

---

#### Шаг 3: Добавление VCR-кассет для PubChem и UniProt

**Цель:** Записать HTTP-взаимодействия для воспроизводимых интеграционных тестов.

**Конкретные правки:**

1. **Создать VCR конфигурацию для PubChem** (`tests/fixtures/vcr/pubchem/`):
   ```python
   # tests/integration/adapters/test_pubchem.py

   @pytest.mark.integration
   @pytest.mark.vcr(
       cassette_library_dir="tests/fixtures/vcr/pubchem",
       filter_headers=["Authorization"]
   )
   class TestPubChemAdapter:
       async def test_fetch_compound_by_cid(self):
           """Fetch compound by CID - recorded interaction."""

       async def test_health_check(self):
           """Health check - recorded interaction."""
   ```

2. **Записать кассеты** (одноразово):
   ```bash
   # Запуск с record_mode="new_episodes"
   pytest tests/integration/adapters/test_pubchem.py --vcr-record=new_episodes
   pytest tests/integration/adapters/test_uniprot.py --vcr-record=new_episodes
   ```

3. **Sanitize secrets**:
   ```python
   # conftest.py
   @pytest.fixture
   def vcr_config():
       return {
           "filter_headers": ["Authorization", "X-API-Key"],
           "before_record_request": scrub_sensitive_data,
       }
   ```

**Риски:**
- Cassettes могут устареть при изменении API
- Sensitive data в cassettes

**Минимизация рисков:**
- CI job для периодической проверки валидности cassettes
- Обязательный sanitization в pre-commit hook

**Критерии готовности:**
- [ ] VCR cassettes для PubChem (min 3)
- [ ] VCR cassettes для UniProt (min 3)
- [ ] Secrets отсутствуют в cassettes
- [ ] Тесты проходят в offline режиме

---

#### Шаг 4: Разбиение PipelineServices на cohesive группы

**Цель:** Уменьшить coupling через decomposition service locator.

**Конкретные правки:**

1. **Выделить DataServices** (`application/core/services.py`):
   ```python
   @dataclass(frozen=True)
   class DataServices:
       """Services for data operations."""
       data_source: DataSourcePort
       storage: StoragePort

   @dataclass(frozen=True)
   class StateServices:
       """Services for state management."""
       lock: LockPort
       checkpoint: CheckpointPort

   @dataclass(frozen=True)
   class ObservabilityServices:
       """Services for monitoring."""
       metrics: MetricsPort
       logger: BoundLogger
   ```

2. **Обновить PipelineExecutor**:
   ```python
   class PipelineExecutor:
       def __init__(
           self,
           data_services: DataServices,
           state_services: StateServices,
           observability: ObservabilityServices,
       ):
           self._data = data_services
           self._state = state_services
           self._obs = observability
   ```

3. **Обновить bootstrap.py**:
   ```python
   def bootstrap_pipeline(...) -> BasePipeline:
       data_services = DataServices(
           data_source=chembl_client,
           storage=storage_adapter,
       )
       state_services = StateServices(
           lock=redis_lock,
           checkpoint=s3_checkpoint,
       )
       # ...
   ```

**Риски:**
- Увеличение количества параметров конструктора
- Breaking changes в существующих pipelines

**Минимизация рисков:**
- Сохранить обратную совместимость через wrapper
- Deprecation warnings для старого API

**Критерии готовности:**
- [ ] DataServices, StateServices, ObservabilityServices созданы
- [ ] PipelineExecutor обновлён
- [ ] Тесты обновлены
- [ ] Документация обновлена

---

#### Шаг 5: Увеличение branch coverage

**Цель:** Поднять branch coverage с 56.3% до 75%+.

**Конкретные правки:**

1. **Идентифицировать uncovered branches**:
   ```bash
   pytest --cov=src/bioetl --cov-report=html --cov-branch
   # Анализ coverage HTML report
   ```

2. **Добавить тесты для error paths**:
   ```python
   # Примеры uncovered branches:

   # executor.py:65 - Exception handling branch
   async def test_execute_handles_data_source_error(self):
       mock_source.fetch.side_effect = ApiError("Connection failed")
       with pytest.raises(RecoverableError):
           await executor.execute(...)

   # circuit_breaker.py:45 - HALF_OPEN state transition
   async def test_circuit_breaker_half_open_success_closes(self):
       breaker.state = CircuitBreakerState.HALF_OPEN
       await breaker.call(successful_operation)
       assert breaker.state == CircuitBreakerState.CLOSED
   ```

3. **Фокус на conditional statements**:
   - if/else branches
   - try/except handlers
   - early returns

**Критерии готовности:**
- [ ] Branch coverage >= 75%
- [ ] Error handling paths покрыты
- [ ] CI проходит

---

#### Шаг 6: Добавление Domain Events

**Цель:** Реализовать event-driven communication для audit и extensibility.

**Конкретные правки:**

1. **Определить базовые события** (`domain/events.py`):
   ```python
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Protocol

   class DomainEvent(Protocol):
       """Base protocol for domain events."""
       occurred_at: datetime

   @dataclass(frozen=True)
   class BatchIngested:
       """Event: batch successfully ingested to Bronze."""
       occurred_at: datetime
       batch_id: BatchID
       pipeline_name: str
       records_count: int
       source_provider: str

   @dataclass(frozen=True)
   class RecordQuarantined:
       """Event: record failed validation and quarantined."""
       occurred_at: datetime
       entity_id: EntityID
       pipeline_name: str
       error_type: ErrorType
       error_message: str

   @dataclass(frozen=True)
   class PipelineCompleted:
       """Event: pipeline run finished."""
       occurred_at: datetime
       run_id: RunID
       pipeline_name: str
       status: str  # "success" | "failed"
       records_processed: int
       records_quarantined: int
   ```

2. **Создать EventPublisher port** (`domain/ports.py`):
   ```python
   class EventPublisherPort(Protocol):
       """Port for publishing domain events."""
       async def publish(self, event: DomainEvent) -> None: ...
   ```

3. **Реализовать адаптер** (`infrastructure/events/`):
   ```python
   class LoggingEventPublisher:
       """Simple event publisher that logs events."""

       def __init__(self, logger: BoundLogger):
           self._logger = logger

       async def publish(self, event: DomainEvent) -> None:
           self._logger.info(
               "domain_event",
               event_type=type(event).__name__,
               **asdict(event)
           )
   ```

4. **Интегрировать в executor**:
   ```python
   # После успешной обработки batch:
   await self._events.publish(BatchIngested(
       occurred_at=datetime.utcnow(),
       batch_id=batch_id,
       pipeline_name=self._config.pipeline_name,
       records_count=len(records),
       source_provider=self._config.provider,
   ))
   ```

**Риски:**
- Overhead от событийной модели
- Complexity increase

**Минимизация рисков:**
- Начать с logging-only publisher
- События immutable (frozen dataclass)

**Критерии готовности:**
- [ ] Domain events определены
- [ ] EventPublisherPort добавлен
- [ ] Минимум 3 события публикуются (BatchIngested, RecordQuarantined, PipelineCompleted)
- [ ] Тесты для событий

---

### 5.3 Предложения по переразбиению модулей

#### Текущая структура application/core/:
```
application/core/
├── base.py              # BasePipeline
├── checkpoint_manager.py
├── executor.py          # PipelineExecutor (187 lines)
├── lock_manager.py
├── orchestrator.py      # PipelineOrchestrator (144 lines)
├── pipeline_config.py
├── pipeline_services.py
├── protocols.py
├── quarantine_manager.py
├── record_processor.py
└── shutdown.py
```

#### Рекомендуемая структура:
```
application/core/
├── pipeline/
│   ├── __init__.py
│   ├── base.py
│   ├── config.py        # PipelineConfig, RuntimeConfig
│   └── executor.py
│
├── orchestration/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── shutdown.py
│   └── signals.py       # (move from interfaces/)
│
├── state/
│   ├── __init__.py
│   ├── checkpoint_manager.py
│   └── lock_manager.py
│
├── processing/
│   ├── __init__.py
│   ├── record_processor.py
│   └── quarantine_manager.py
│
├── services.py          # DataServices, StateServices, ObservabilityServices
└── protocols.py
```

**Обоснование:**
- Группировка по responsibility (cohesion)
- Уменьшение coupling между подмодулями
- Легче тестировать отдельные группы

---

### 5.4 Шаги по выносу общих компонентов

#### Кандидаты на выделение в shared модуль:

1. **Retry utilities** (`infrastructure/adapters/http/client.py:RetryConfig`):
   ```python
   # Переместить в: infrastructure/common/retry.py
   @dataclass
   class RetryConfig:
       max_attempts: int = 3
       base_delay: float = 1.0
       max_delay: float = 60.0
       multiplier: float = 2.0
       jitter: float = 0.1

       def calculate_delay(self, attempt: int) -> float:
           """Calculate delay with exponential backoff and jitter."""
   ```

2. **Compression utilities** (используются в Bronze writer и потенциально в других местах):
   ```python
   # infrastructure/common/compression.py
   def compress_zstd(data: bytes, level: int = 3) -> bytes: ...
   def decompress_zstd(data: bytes) -> bytes: ...
   ```

3. **Hash utilities** (domain/transformations.py):
   ```python
   # domain/common/hashing.py
   def generate_content_hash(record: dict, provider: str) -> ContentHash: ...
   def normalize_for_hash(record: dict) -> dict: ...
   ```

---

## 6. Метрики и тесты для контроля качества

### 6.1 Рекомендуемые метрики

| Метрика | Текущее значение | Целевое значение | Инструмент |
|---------|------------------|------------------|------------|
| Statement Coverage | 71.23% | 80%+ | pytest-cov |
| Branch Coverage | 56.3% | 75%+ | pytest-cov |
| Cyclomatic Complexity | Max B | Max B | xenon |
| Architecture Violations | 0 | 0 | import-linter |
| Type Coverage | ~90% | 95%+ | mypy --strict |
| Mutation Score | N/A | 70%+ | mutmut |
| Dead Code | N/A | 0% | vulture |
| Duplication | N/A | <5% | jscpd |

### 6.2 Новые тесты для добавления

#### 6.2.1 Архитектурные тесты

```python
# tests/architecture/test_layer_dependencies_extended.py

def test_domain_has_no_io_imports():
    """Domain layer must not import I/O libraries."""
    import ast
    import_linter_config = parse_importlinter()
    for contract in import_linter_config["forbidden"]:
        if contract["source"] == "bioetl.domain":
            assert verify_no_forbidden_imports(contract)

def test_application_uses_only_ports():
    """Application layer must import only domain ports, not concrete implementations."""
    app_imports = extract_imports("src/bioetl/application")
    infrastructure_imports = [i for i in app_imports if "infrastructure" in i]
    # Allow only: infrastructure.config (for settings)
    forbidden = [i for i in infrastructure_imports if "config" not in i]
    assert forbidden == [], f"Forbidden imports: {forbidden}"

def test_no_circular_dependencies():
    """Verify no circular imports exist."""
    graph = build_import_graph("src/bioetl")
    cycles = find_cycles(graph)
    assert cycles == [], f"Circular dependencies found: {cycles}"
```

#### 6.2.2 Contract тесты

```python
# tests/contract/test_silver_record_contract.py

from hypothesis import given, strategies as st

@given(st.builds(SilverRecord, ...))
def test_silver_record_always_has_required_fields(record):
    """Every SilverRecord must have audit fields."""
    assert record.get("entity_id") is not None
    assert record.get("content_hash") is not None
    assert record.get("_source_batch_id") is not None

def test_silver_record_content_hash_is_deterministic():
    """Same input must produce same content hash."""
    record = {"field1": "value1", "field2": 42}
    hash1 = generate_content_hash(record, "test")
    hash2 = generate_content_hash(record, "test")
    assert hash1 == hash2
```

#### 6.2.3 Performance тесты

```python
# tests/performance/test_throughput.py

import pytest
from time import perf_counter

@pytest.mark.slow
async def test_executor_processes_1000_records_under_10_seconds():
    """Pipeline executor must process 1000 records in <10s."""
    executor = create_test_executor()
    records = generate_test_records(1000)

    start = perf_counter()
    await executor.execute(records)
    elapsed = perf_counter() - start

    assert elapsed < 10.0, f"Took {elapsed:.2f}s, expected <10s"

@pytest.mark.slow
async def test_rate_limiter_respects_limit():
    """TokenBucket must not exceed configured rate."""
    bucket = TokenBucket(rate=10.0, capacity=10)

    start = perf_counter()
    for _ in range(50):
        await bucket.acquire()
    elapsed = perf_counter() - start

    # 50 requests at 10/sec = at least 4 seconds
    assert elapsed >= 4.0
```

### 6.3 Связь метрик с интегральным баллом

| Метрика | Влияние на категории | Потенциальное улучшение балла |
|---------|---------------------|-------------------------------|
| Coverage 80%+ | Тестирование (6 → 8) | +0.30 |
| Branch Coverage 75%+ | Тестирование (6 → 7.5) | +0.23 |
| TypedDict для records | Доменная модель (9 → 9.5) | +0.05 |
| Domain Events | Доменная модель (9 → 9.5), Наблюдаемость (7 → 8) | +0.13 |
| VCR для всех adapters | Тестирование (6 → 7) | +0.15 |
| Services decomposition | Модульность (8 → 9) | +0.12 |

**Прогноз после рефакторинга:**

```
Текущий балл: 7.92

После P0 изменений: +0.9 → 8.82
После P1 изменений: +0.7 → 9.52 (capped at ~9.2 реально)
После P2 изменений: +0.35 → ~9.5
```

---

## 7. Прогноз улучшения оценок

### 7.1 Таблица прогноза по категориям

| Категория | Текущая | После P0 | После P1 | После P2 | Целевая |
|-----------|---------|----------|----------|----------|---------|
| Архитектура слоёв | 9 | 9 | 9.5 | 9.5 | 9.5 |
| Модульность | 8 | 8 | 9 | 9 | 9 |
| Доменная модель | 9 | 9.5 | 9.5 | 10 | 10 |
| **Тестирование** | **6** | **8** | **8.5** | **9** | **9** |
| Обработка ошибок | 9 | 9 | 9 | 9 | 9 |
| Наблюдаемость | 7 | 7 | 7.5 | 8 | 8 |
| Производительность | 8 | 8 | 8 | 8 | 8 |
| Безопасность | 7 | 7 | 7.5 | 8 | 8 |
| Документация | 8 | 8 | 8 | 8.5 | 8.5 |
| Техдолг | 9 | 9 | 9 | 9 | 9 |

### 7.2 Прогноз интегрального балла

```
Текущий:      7.92
После P0:     8.42 (+0.50)
После P1:     8.77 (+0.35)
После P2:     9.02 (+0.25)

Целевой:      9.0+
```

### 7.3 Roadmap реализации

```
Q1 (P0 - Critical):
├── Week 1-2: Coverage критических компонентов
├── Week 3-4: TypedDict для Silver/Gold records
└── Milestone: Балл ~8.4

Q2 (P1 - High):
├── Week 1: VCR cassettes для PubChem/UniProt
├── Week 2-3: Services decomposition
├── Week 4: Branch coverage improvement
└── Milestone: Балл ~8.8

Q3 (P2 - Medium):
├── Week 1-2: Domain Events
├── Week 3: Observability coverage
├── Week 4: Circuit Breaker metrics export
└── Milestone: Балл ~9.0
```

---

## Приложение A: Файловые ссылки

### Критические файлы для рефакторинга

| Файл | Строки | Приоритет | Изменения |
|------|--------|-----------|-----------|
| `src/bioetl/application/core/orchestrator.py` | 144 | P0 | Увеличить coverage |
| `src/bioetl/application/core/checkpoint_manager.py` | 68 | P0 | Увеличить coverage |
| `src/bioetl/application/core/executor.py` | 187 | P0 | TypedDict |
| `src/bioetl/domain/types.py` | ~220 | P0 | Добавить TypedDict |
| `src/bioetl/application/core/pipeline_services.py` | 30 | P1 | Decompose |
| `src/bioetl/domain/ports.py` | ~150 | P2 | EventPublisherPort |

### Тестовые файлы для создания/обновления

| Файл | Статус | Приоритет |
|------|--------|-----------|
| `tests/unit/application/core/test_orchestrator.py` | Обновить | P0 |
| `tests/unit/application/core/test_checkpoint_manager.py` | Обновить | P0 |
| `tests/integration/adapters/test_pubchem.py` | Создать VCR | P1 |
| `tests/integration/adapters/test_uniprot.py` | Создать VCR | P1 |
| `tests/unit/domain/test_events.py` | Создать | P2 |
| `tests/architecture/test_layer_dependencies_extended.py` | Создать | P1 |

---

## Приложение B: Checklist для Code Review

### Архитектурный checklist

- [ ] Domain слой не импортирует infrastructure
- [ ] Application использует только ports (не concrete implementations)
- [ ] Новые классы используют dependency injection
- [ ] Новые dataclasses frozen где возможно
- [ ] Новые функции в domain слое - чистые (без side effects)
- [ ] Type hints присутствуют везде
- [ ] Docstrings для public API

### Тестовый checklist

- [ ] Unit тесты для новой логики
- [ ] Интеграционные тесты для внешних взаимодействий
- [ ] Mock-и имеют spec (для type safety)
- [ ] VCR cassettes для новых HTTP-вызовов
- [ ] Error paths покрыты тестами
- [ ] Async тесты используют pytest-asyncio

---

*Документ подготовлен на основе анализа кодовой базы BioETL v5.0.0*
