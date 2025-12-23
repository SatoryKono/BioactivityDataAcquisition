# Архитектурный Обзор BioETL

*Версия: 2.0*
*Дата: 2025-12-23*
*Статус: Полный аудит (deep dive)*

---

## Содержание

1. [Резюме](#1-резюме)
2. [Числовая оценка по 10 категориям](#2-числовая-оценка-по-10-категориям)
3. [Детальный анализ архитектуры](#3-детальный-анализ-архитектуры)
4. [Выявленные проблемы](#4-выявленные-проблемы)
5. [План рефакторинга](#5-план-рефакторинга)
6. [Метрики и тесты для контроля качества](#6-метрики-и-тесты-для-контроля-качества)
7. [Приложения](#7-приложения)

---

## 1. Резюме

### 1.1 Общая Характеристика

**BioETL** — production-grade фреймворк для ETL биоактивных данных из ChEMBL, PubChem, UniProt и PubMed. Построен на принципах:

- **Hexagonal Architecture (Ports & Adapters)** — строгое разделение слоёв
- **Medallion Architecture** — Bronze/Silver/Gold data layers с Delta Lake
- **Domain-Driven Design** — изолированная доменная логика с frozen dataclasses
- **Local-Only Deployment** — MemoryLock + LocalCheckpoint (ADR-010)

### 1.2 Ключевые Метрики Кодовой Базы

| Метрика | Значение |
|---------|----------|
| Python файлов (src/) | 133 |
| Строк кода (src/) | ~10,000 |
| Тестовых файлов | 122 |
| Тестов | 1,073 |
| Протоколов (Ports) | 10 |
| Domain Entities | 10 |
| Пайплайнов | 9 |
| ADR документов | 11 |
| Покрытие тестами | >80% |

### 1.3 Интегральный Балл

## **8.52 / 10** — Очень Хороший

| Диапазон | Статус | Описание |
|----------|--------|----------|
| 0.0 – 4.9 | 🔴 Критический | Требуется капитальный рефакторинг |
| 5.0 – 6.9 | 🟡 Удовлетворительный | Значительные улучшения необходимы |
| 7.0 – 7.9 | 🟢 Хороший | Готов к production с оговорками |
| **8.0 – 8.9** | **🟢 Очень Хороший** | **Production-ready, minor improvements** |
| 9.0 – 10.0 | 🟢 Отличный | Эталонная реализация |

**Вывод**: Проект готов к production. Архитектура слоёв соблюдается идеально. Основная область для улучшения — Dependency Injection в application layer.

### 1.4 Статус Критических Проблем

| ID | Проблема | Статус |
|----|----------|--------|
| **P1-DI** | 12 нарушений DI в application layer | ⚠️ Требует рефакторинга |
| **P1-NEW** | `validated_records` undefined | ✅ Исправлено ранее |
| **P2-NEW** | GoldValidator дублирование | ✅ Исправлено ранее |

---

## 2. Числовая Оценка по 10 Категориям

### 2.1 Методология

- **Шкала**: 1-10 (1 — критические проблемы, 10 — эталонная реализация)
- **Веса**: Распределены по важности для production-системы (сумма = 100%)
- **Взвешенный балл**: Оценка × Вес

### 2.2 Таблица Оценок

| № | Категория | Описание | Вес | Оценка | Взвешенный | Обоснование |
|---|-----------|----------|-----|--------|------------|-------------|
| 1 | **Архитектура слоёв** | Соблюдение Ports & Adapters, матрица импортов | 15% | 9.5 | 1.43 | 0 нарушений импортов, 16 архитектурных тестов, 4 import-linter контракта |
| 2 | **Модульность и связность** | Cohesion модулей, coupling, границы | 12% | 8.5 | 1.02 | Хорошее разделение по провайдерам. Минус: жёсткие связи в трансформерах |
| 3 | **Качество доменной модели** | Value Objects, Entities, чистота от I/O | 12% | 10.0 | 1.20 | Эталон: 100% frozen dataclasses, 10 Protocol ports, 18 pure functions |
| 4 | **Dependency Injection** | DI через конструкторы, Composition Root | 12% | 6.0 | 0.72 | **12 нарушений**: трансформеры и менеджеры создаются внутри классов |
| 5 | **Тестирование** | Покрытие, VCR, архитектурные тесты | 10% | 8.5 | 0.85 | 1073 теста, 81% покрытие, 36 VCR кассет, строгие arch tests |
| 6 | **Обработка ошибок** | Классификация, retry, circuit breaker | 10% | 9.0 | 0.90 | 21 custom исключения, ADR-007/008, threshold-политики |
| 7 | **Логирование и наблюдаемость** | Structured logs, metrics, tracing | 8% | 8.5 | 0.68 | structlog + run_id, Prometheus, OpenTelemetry опционально |
| 8 | **Производительность** | Rate limiting, async I/O, Delta Lake | 7% | 8.0 | 0.56 | TokenBucket, async httpx, Delta merge/vacuum/optimize |
| 9 | **Безопасность** | Секреты, PII handling, VCR санитизация | 7% | 8.0 | 0.56 | Env-based secrets, PII hashing в Silver, VCR санитизация |
| 10 | **Документация** | ADR, RULES.md, docstrings | 7% | 8.5 | 0.60 | 11 ADR, RULES.md v5.2, Google Style docstrings на русском |

### 2.3 Расчёт Интегрального Балла

```
Σ (Вес × Оценка) = 1.43 + 1.02 + 1.20 + 0.72 + 0.85 + 0.90 + 0.68 + 0.56 + 0.56 + 0.60 = 8.52
```

### 2.4 Детализация по Категориям

#### Категория 1: Архитектура слоёв (9.5/10)

**Сильные стороны:**
- 0 нарушений матрицы импортов
- Строгое разделение: domain → application → composition → infrastructure
- 16 архитектурных тестов в `tests/architecture/`
- 4 контракта import-linter

**Структура:**
```
src/bioetl/
├── domain/          2,658 LOC  — Protocols, Entities, Pure Functions
├── application/     1,874 LOC  — Pipelines, Use Cases, Orchestration
├── composition/     1,332 LOC  — DI Container, Factories, Bootstrap
├── infrastructure/  ~4,000 LOC — Adapters, Storage, HTTP Client
└── interfaces/      ~200 LOC   — CLI (Click-based)
```

#### Категория 3: Качество доменной модели (10.0/10)

**Эталонная реализация:**
- 10 frozen dataclasses с инвариантами
- 10 Protocol-based ports
- 18 чистых функций в `transformations.py`
- 21 структурированное исключение
- 100% type hints с NewType для семантики

#### Категория 4: Dependency Injection (6.0/10)

**Проблемы (12 нарушений):**

| Файл | Строка | Нарушение |
|------|--------|-----------|
| `pipelines/chembl/activity.py` | 35 | `ActivityTransformer(provider=...)` создаётся внутри |
| `pipelines/chembl/assay.py` | 35 | `AssayTransformer(provider=...)` |
| `pipelines/chembl/molecule.py` | 35 | `MoleculeTransformer(provider=...)` |
| `pipelines/chembl/target.py` | 35 | `TargetTransformer(provider=...)` |
| `pipelines/chembl/target_component.py` | 37 | `TargetComponentTransformer(provider=...)` |
| `pipelines/chembl/document.py` | 35 | `DocumentTransformer(provider=...)` |
| `pipelines/pubchem/compound.py` | 20 | `PubChemCompoundTransformer(provider=...)` |
| `pipelines/pubmed/publications.py` | 19 | `PubMedPublicationTransformer(provider=...)` |
| `pipelines/uniprot/protein.py` | 20 | `UniProtProteinTransformer(provider=...)` |
| `core/record_processor.py` | 53 | `QuarantineManager(...)` |
| `core/record_processor.py` | 74 | `BatchMetricsRecorder(...)` |
| `core/runner.py` | 59 | `LockManager.create(...)` |

---

## 3. Детальный Анализ Архитектуры

### 3.1 Соблюдение Слоистой Структуры

#### Матрица Импортов (100% соблюдение)

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ❌ 0 | ❌ 0 | ❌ 0 | ❌ 0 |
| **application** | ✅ | ✅ | ❌ 0 | ❌ 0 | ❌ 0 |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ 0 |
| **infrastructure** | ✅ | ❌ 0 | ❌ 0 | ✅ | ❌ 0 |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Проверено:**
- Grep по всем файлам
- AST парсинг
- import-linter contracts
- `tests/architecture/test_layer_dependencies.py`

### 3.2 Ports & Adapters

#### Domain Ports (10 Protocols)

| Port | Методы | Async | Адаптеры |
|------|--------|-------|----------|
| `DataSourcePort` | 4 | Yes | ChemblAdapter, PubChemClient, UniProtClient, PubMedAdapter |
| `StoragePort` | 6 | Yes | BronzeWriter, DeltaWriter, GoldWriter |
| `InputFilterPort` | 1 | Yes | CsvFilterReader |
| `CheckpointPort` | 5 | Yes | LocalCheckpoint |
| `LockPort` | 4 | Yes | MemoryLock |
| `QuarantinePort` | 4 | Yes | UnifiedQuarantine |
| `MetricsPort` | 2 | No | PrometheusMetrics, NoOpMetrics |
| `LoggerPort` | 5 | No | structlog wrapper |
| `TracingPort` | 1 | No | OpenTelemetryTracer, NoOpTracer |
| `GoldValidatorPort` | 1 | No | PanderaGoldValidator, NoOpGoldValidator |

#### Infrastructure Adapters Quality

| Adapter | Health Check | Rate Limiting | Circuit Breaker | Retry |
|---------|-------------|---------------|-----------------|-------|
| ChemblAdapter | ✅ `/status.json` | ⚠️ Via CB only | ✅ | ✅ |
| PubChemClient | ✅ Probe | ✅ TokenBucket(5/s) | ✅ | ✅ |
| UniProtClient | ✅ Search probe | ✅ TokenBucket(100/s) | ✅ | ✅ |
| PubMedAdapter | ✅ esearch probe | ✅ TokenBucket(10/s) | ✅ | ✅ |

### 3.3 Domain Layer Quality

#### Entities (10 frozen dataclasses)

```python
@dataclass(frozen=True)  # Immutable
class Activity(BaseEntity):
    """128 полей с полной типизацией."""
    activity_id: str
    molecule_chembl_id: str | None
    pchembl_value: float | None
    # ...

    def __post_init__(self):
        super().__post_init__()
        self._validate_invariants()  # Валидация при создании
```

#### Pure Functions (transformations.py)

```python
# 18 чистых функций (no side effects, no I/O)
def generate_content_hash(record: dict, provider: str) -> ContentHash:
    """SHA256 для версионирования."""

@singledispatch
def _normalize_value(value: Any) -> Any:
    """Нормализация: NaN→None, floats→round(10)."""
```

### 3.4 Composition Root

**Bootstrap Flow:**
```
bootstrap_pipeline(ctx)
├── load_pipeline_config()
├── bootstrap_logger()
├── bootstrap_tracer()
├── FilterConfigBuilder.build()
├── PipelineRegistry.get(name) → factory
└── factory.create_runner()
    ├── create_with_services()
    │   ├── StorageFactory.create() → Bronze/Silver/Gold
    │   ├── BaseServicesFactory.create_common_services()
    │   │   ├── _create_lock() → MemoryLock
    │   │   ├── _create_checkpoint() → LocalCheckpoint
    │   │   ├── _create_quarantine() → UnifiedQuarantine
    │   │   └── _create_metrics() → PrometheusMetrics
    │   └── create_data_source() → DataSourcePort
    └── PipelineRunner(executor, checkpoint_manager, ...)
```

### 3.5 Test Coverage

| Уровень | Файлов | Тестов | LOC | Покрытие |
|---------|--------|--------|-----|----------|
| **Unit** | 94 | 919 | 16,959 | ~85% |
| **Integration** | 14 | ~100 | 1,572 | VCR-based |
| **E2E** | 11 | ~40 | ~1,500 | Full cycle |
| **Architecture** | 3 | 17 | — | Layer validation |
| **ИТОГО** | 122 | 1,073 | 19,531 | >80% |

---

## 4. Выявленные Проблемы

### 4.1 P1: Критические — Нарушения DI (12 файлов)

#### P1.1: Трансформеры создаются внутри пайплайнов (9 файлов)

**Проблема:**
```python
# src/bioetl/application/pipelines/chembl/activity.py:35
class ChEMBLActivityPipeline(BasePipeline):
    def __init__(self, config, runtime, services):
        super().__init__(config, runtime, services)
        self._transformer = ActivityTransformer(provider=self.provider)  # ❌ НАРУШЕНИЕ
```

**Последствия:**
- Невозможно подменить трансформер в тестах
- Жёсткая связанность с конкретной реализацией
- Нарушает Open/Closed Principle

**Затронутые файлы:**
```
src/bioetl/application/pipelines/chembl/activity.py:35
src/bioetl/application/pipelines/chembl/assay.py:35
src/bioetl/application/pipelines/chembl/molecule.py:35
src/bioetl/application/pipelines/chembl/target.py:35
src/bioetl/application/pipelines/chembl/target_component.py:37
src/bioetl/application/pipelines/chembl/document.py:35
src/bioetl/application/pipelines/pubchem/compound.py:20
src/bioetl/application/pipelines/pubmed/publications.py:19
src/bioetl/application/pipelines/uniprot/protein.py:20
```

#### P1.2: Менеджеры создаются в RecordProcessor (2 нарушения)

**Файл:** `src/bioetl/application/core/record_processor.py`

```python
# Строка 53 — QuarantineManager создаётся внутри
self._quarantine_manager = QuarantineManager(...)  # ❌

# Строка 74 — BatchMetricsRecorder создаётся внутри
self._batch_metrics = BatchMetricsRecorder(...)  # ❌
```

#### P1.3: LockManager.create() в PipelineRunner

**Файл:** `src/bioetl/application/core/runner.py:59`

```python
self._lock_manager = LockManager.create(...)  # ❌ Factory внутри application
```

### 4.2 P2: Средние — Тестовое Покрытие

| Компонент | Проблема | Влияние |
|-----------|----------|---------|
| PubChem E2E | Тест пропущен (skip) | Регрессии могут остаться незамеченными |
| Composition factories | ~70% покрытие | DI ошибки проявятся в runtime |

### 4.3 P3: Низкие — Code Smells

| Проблема | Файл | Описание |
|----------|------|----------|
| Activity entity 128 полей | `domain/entities.py` | Кандидат на разбиение на Value Objects |
| Defensive getattr в CLI | `interfaces/cli.py` | `getattr(runner, "logger", None)` |
| Implicit registration | `composition/bootstrap.py` | `import ... # noqa: F401` side-effect |

---

## 5. План Рефакторинга

### 5.1 Приоритет 0: Критические (Блокеры DI)

#### R0.1: Инжектировать трансформеры в пайплайны

**Цель:** Соблюдение принципа DI — зависимости передаются в конструктор

**Конкретные правки:**

**1. Изменить BasePipeline:**
```python
# src/bioetl/application/core/base.py
class BasePipeline(ABC):
    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        transformer: BaseTransformer,  # ДОБАВИТЬ
    ):
        self._transformer = transformer
```

**2. Обновить все 9 пайплайнов:**
```python
# src/bioetl/application/pipelines/chembl/activity.py
class ChEMBLActivityPipeline(BasePipeline):
    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        transformer: ActivityTransformer,  # ИНЖЕКТИРОВАТЬ
    ):
        super().__init__(config, runtime, services, transformer)
        # УДАЛИТЬ: self._transformer = ActivityTransformer(...)
```

**3. Добавить transformer_class в GenericPipelineFactory:**
```python
# src/bioetl/composition/factories/generic_factory.py
class GenericPipelineFactory:
    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[BasePipeline],
        provider: str,
        transformer_class: type[BaseTransformer],  # ДОБАВИТЬ
        ...
    ):
        self.transformer_class = transformer_class

    def _create_transformer(self) -> BaseTransformer:
        return self.transformer_class(provider=self.provider)
```

**4. Обновить pipeline_factories.py:**
```python
# src/bioetl/composition/factories/pipeline_factories.py
chembl_activity_factory = GenericPipelineFactory(
    pipeline_name="chembl_activity",
    pipeline_class=ChEMBLActivityPipeline,
    provider="chembl",
    transformer_class=ActivityTransformer,  # ДОБАВИТЬ
    silver_schema=CHEMBL_ACTIVITY_SCHEMA,
    gold_schema=ChEMBLActivityGoldSchema,
)
```

**Риски:**
- Изменение сигнатуры конструкторов потребует обновления тестов
- **Минимизация:** Постепенное обновление, по одному пайплайну

**Критерии "готово":**
- [ ] Все 9 пайплайнов принимают трансформер в конструктор
- [ ] GenericPipelineFactory создаёт трансформеры
- [ ] Все unit-тесты пайплайнов проходят
- [ ] `make lint && make test` успешно

#### R0.2: Инжектировать менеджеры в RecordProcessor

**Цель:** Убрать создание зависимостей из RecordProcessor

**Конкретные правки:**
```python
# src/bioetl/application/core/record_processor.py
class RecordProcessor:
    def __init__(
        self,
        services: PipelineServices,
        quarantine_manager: QuarantineManager,  # ДОБАВИТЬ (не Optional)
        batch_metrics: BatchMetricsRecorder,     # ДОБАВИТЬ (не Optional)
        error_classifier: ErrorClassifier,
        ...
    ):
        self._quarantine_manager = quarantine_manager
        self._batch_metrics = batch_metrics
        # УДАЛИТЬ создание внутри __init__
```

**Обновить GenericPipelineFactory:**
```python
def _create_record_processor(self, pipeline, ...):
    quarantine_manager = QuarantineManager(
        quarantine_port=pipeline.services.quarantine,
        pipeline_name=pipeline.config.name,
    )
    batch_metrics = BatchMetricsRecorder(
        pipeline.services.metrics,
        pipeline_label=pipeline.config.name,
        run_type_label=pipeline.runtime.run_type.value,
    )
    return RecordProcessor(
        services=pipeline.services,
        quarantine_manager=quarantine_manager,
        batch_metrics=batch_metrics,
        ...
    )
```

**Критерии "готово":**
- [ ] RecordProcessor не создаёт зависимости внутри
- [ ] Фабрика создаёт и инжектирует менеджеры
- [ ] Unit-тесты RecordProcessor можно упростить (мокировать менеджеры)

#### R0.3: Вынести создание LockManager в composition

**Цель:** LockManager создаётся в фабрике, не в runner

**Конкретные правки:**
```python
# src/bioetl/application/core/runner.py
class PipelineRunner:
    def __init__(
        self,
        ...,
        lock_manager: LockManager,  # ДОБАВИТЬ
    ):
        self._lock_manager = lock_manager
        # УДАЛИТЬ: self._lock_manager = LockManager.create(...)
```

**Обновить GenericPipelineFactory:**
```python
def create_runner(self, ...):
    lock_manager = LockManager.create(
        lock_port=services.lock,
        run_id=run_id,
        pipeline_name=self.pipeline_name,
        provider=self.provider,
        run_type=runtime.run_type,
        ...
    )
    return PipelineRunner(
        ...,
        lock_manager=lock_manager,
    )
```

**Критерии "готово":**
- [ ] LockManager инжектируется в PipelineRunner
- [ ] GenericPipelineFactory создаёт LockManager
- [ ] Тесты runner не требуют патчинга LockManager.create

### 5.2 Приоритет 1: Высокие (Production Quality)

#### R1.1: Покрыть PubChem E2E тестами

**Цель:** Устранить пропущенный E2E тест

**Действия:**
1. Исследовать причину skip (deprecated canonical_smiles)
2. Обновить VCR кассету или адаптер
3. Включить тест обратно

**Критерии "готово":**
- [ ] `test_pubchem_compound_e2e.py` проходит без skip
- [ ] VCR кассета записана и санитизирована

#### R1.2: Увеличить покрытие composition factories

**Цель:** Покрытие >80% для всех фабрик

**Действия:**
1. Добавить unit-тесты для GenericPipelineFactory.create_runner()
2. Добавить тесты для edge cases в StorageFactory
3. Добавить тесты для DataSourceRegistry creators

**Критерии "готово":**
- [ ] Покрытие composition/ >80%
- [ ] Все фабрики имеют тесты на create методы

### 5.3 Приоритет 2: Средние (Code Quality)

#### R2.1: Разбить Activity entity на Value Objects (Опционально)

**Цель:** Уменьшить размер Activity (128 полей)

**Предложение:**
```python
@dataclass(frozen=True)
class ActivityMeasurement:
    """Value Object для измерений."""
    standard_value: float | None
    standard_units: str | None
    standard_type: str | None
    pchembl_value: float | None

@dataclass(frozen=True)
class Activity(BaseEntity):
    """Упрощённая Activity с вложенными VO."""
    activity_id: str
    measurement: ActivityMeasurement
    molecule_chembl_id: str | None
    # ... остальные поля
```

**Риски:**
- Breaking change для Silver схемы
- **Минимизация:** Версионирование схемы (`activity_v2`)

#### R2.2: Явная регистрация пайплайнов

**Цель:** Заменить implicit import на explicit registration

```python
# bootstrap.py — ТЕКУЩИЙ КОД
import bioetl.composition.factories.pipeline_factories  # noqa: F401

# bootstrap.py — ПРЕДЛАГАЕМЫЙ КОД
from bioetl.composition.factories.pipeline_factories import register_all_pipelines

def bootstrap_pipeline(ctx):
    register_all_pipelines()  # Явный вызов
    ...
```

#### R2.3: Добавить property для logger в PipelineRunner

**Цель:** Устранить defensive getattr в CLI

```python
# runner.py — ДОБАВИТЬ
@property
def logger(self) -> LoggerPort:
    """Логгер пайплайна."""
    return self._logger

# cli.py — ИЗМЕНИТЬ
logger = runner.logger  # Без getattr
```

### 5.4 Сводная Таблица Плана

| Фаза | Задача | Приоритет | Усилия | Изменение балла |
|------|--------|-----------|--------|-----------------|
| **0** | R0.1 Инжектировать трансформеры | 🔴🔴 | 2-3 ч | +2.0 (кат. 4) |
| **0** | R0.2 Инжектировать менеджеры | 🔴🔴 | 1 ч | +0.5 (кат. 4) |
| **0** | R0.3 Вынести LockManager | 🔴 | 30 мин | +0.5 (кат. 4) |
| **1** | R1.1 PubChem E2E | 🟡 | 1-2 ч | +0.25 (кат. 5) |
| **1** | R1.2 Factory tests | 🟡 | 2-3 ч | +0.25 (кат. 5) |
| **2** | R2.1 Activity VO | 🟢 | 4-8 ч | 0 (уже 10) |
| **2** | R2.2 Explicit registration | 🟢 | 15 мин | +0.25 (кат. 2) |
| **2** | R2.3 Logger property | 🟢 | 10 мин | +0.1 (кат. 10) |

### 5.5 Прогноз Изменения Балла

| Этап | Категория | Текущая | После | Изменение |
|------|-----------|---------|-------|-----------|
| После R0.1-R0.3 | #4 DI | 6.0 | 9.0 | +3.0 |
| После R1.1-R1.2 | #5 Tests | 8.5 | 9.0 | +0.5 |
| После R2.2 | #2 Модульность | 8.5 | 9.0 | +0.5 |

**Расчёт нового балла после полного рефакторинга:**

```
Категория 4: 6.0 → 9.0, вес 12%: +0.36
Категория 5: 8.5 → 9.0, вес 10%: +0.05
Категория 2: 8.5 → 9.0, вес 12%: +0.06

Новый балл: 8.52 + 0.36 + 0.05 + 0.06 = 8.99 ≈ 9.0
```

**После рефакторинга: 9.0 / 10 (Отличный)**

---

## 6. Метрики и Тесты для Контроля Качества

### 6.1 Автоматизированные Метрики

| Метрика | Инструмент | Порог | Категория |
|---------|------------|-------|-----------|
| Import violations | import-linter | 0 | #1 Архитектура |
| Line coverage | pytest-cov | ≥80% | #5 Тестирование |
| Cyclomatic complexity | radon | ≤5 (domain) | #3 Domain |
| Type errors | mypy --strict | 0 | #3 Domain |
| Linting errors | ruff | 0 | #10 Сопровождаемость |
| DI violations | Новый тест | 0 | #4 DI |

### 6.2 Новые Архитектурные Тесты (Предложение)

#### test_di_violations.py
```python
def test_no_dependency_creation_in_pipelines():
    """Проверяет, что пайплайны не создают трансформеры."""
    for py_file in pipelines_path.rglob("*.py"):
        content = py_file.read_text()
        # Проверка на паттерн: Transformer(provider=
        matches = re.findall(r"\w+Transformer\(provider=", content)
        assert not matches, f"DI violation in {py_file}: {matches}"

def test_pipelines_accept_transformer_in_constructor():
    """Проверяет, что все пайплайны принимают трансформер."""
    for pipeline_class in ALL_PIPELINE_CLASSES:
        sig = inspect.signature(pipeline_class.__init__)
        assert "transformer" in sig.parameters, f"{pipeline_class} missing transformer param"
```

### 6.3 Команды для Проверки

```bash
# Полная проверка качества
make lint          # ruff + mypy
make test          # pytest с coverage
make arch-lint     # import-linter
make arch-test     # architecture tests

# Новые команды (предложение)
make di-check      # проверка DI нарушений
make complexity    # xenon (CC thresholds)
make security      # pip-audit + bandit
```

### 6.4 Связь Метрик с Интегральным Баллом

| Категория | Метрика | Влияние |
|-----------|---------|---------|
| #1 Архитектура | import-linter violations | -0.5 за каждое |
| #3 Domain | mypy errors | -0.1 за каждые 10 |
| #4 DI | DI violations count | -0.25 за каждое |
| #5 Tests | coverage % | -0.2 за каждые 10% ниже 80% |
| #8 Security | HIGH severity CVEs | -0.3 за каждую |

---

## 7. Приложения

### 7.1 Архитектурные Решения (ADR)

| ADR | Название | Статус |
|-----|----------|--------|
| ADR-001 | Delta Lake vs Parquet | ✅ Accepted |
| ADR-002 | Medallion Architecture | ✅ Accepted |
| ADR-003 | Redis for Distributed Locking | ⛔ Superseded by ADR-010 |
| ADR-004 | Pydantic vs Dataclasses | ✅ Accepted |
| ADR-005 | Composition Layer Separation | ✅ Accepted |
| ADR-006 | Logger and Metrics Ports | ✅ Accepted |
| ADR-007 | Circuit Breaker Implementation | ✅ Accepted |
| ADR-008 | Graceful Shutdown Strategy | ✅ Accepted |
| ADR-009 | PaginatedFetcherMixin Design | ✅ Accepted |
| ADR-010 | Local-Only Deployment | ✅ Accepted |
| ADR-011 | Remove Watermark Mechanism | ✅ Accepted |

### 7.2 Файлы с DI Нарушениями

```
# Пайплайны (9 файлов)
src/bioetl/application/pipelines/chembl/activity.py:35
src/bioetl/application/pipelines/chembl/assay.py:35
src/bioetl/application/pipelines/chembl/molecule.py:35
src/bioetl/application/pipelines/chembl/target.py:35
src/bioetl/application/pipelines/chembl/target_component.py:37
src/bioetl/application/pipelines/chembl/document.py:35
src/bioetl/application/pipelines/pubchem/compound.py:20
src/bioetl/application/pipelines/pubmed/publications.py:19
src/bioetl/application/pipelines/uniprot/protein.py:20

# Core (3 файла)
src/bioetl/application/core/record_processor.py:53,74
src/bioetl/application/core/runner.py:59
```

### 7.3 Структура Тестов

```
tests/
├── unit/                  # 94 файла, 919 тестов
│   ├── domain/            # Ports, entities, types
│   ├── application/       # Pipelines, transformers, core
│   ├── infrastructure/    # Adapters, storage, http
│   └── composition/       # Factories
├── integration/           # 14 файлов, ~100 тестов (VCR)
├── e2e/                   # 11 файлов, ~40 тестов
├── architecture/          # 3 файла, 17 тестов
└── fixtures/vcr/          # 36 VCR кассет
```

### 7.4 Зависимости Проекта

**Core:**
- `httpx>=0.27` — async HTTP
- `pydantic>=2.0` — validation
- `polars>=1.0` — data processing
- `deltalake>=0.18` — Delta Lake
- `pandera>=0.20` — schema validation

**Observability:**
- `prometheus-client>=0.20` — metrics
- `structlog>=24.0` — logging
- `opentelemetry-*` — tracing (optional)

**Dev:**
- `pytest>=8.0`, `hypothesis>=6.100` — testing
- `mypy>=1.10`, `ruff>=0.4` — static analysis
- `import-linter>=2.0` — architecture enforcement

---

## Заключение

**BioETL** — зрелый production-grade проект с:

✅ **Эталонной архитектурой слоёв** (0 нарушений импортов)
✅ **Отличной доменной моделью** (10/10)
✅ **Comprehensive тестированием** (1073 теста, >80% coverage)
✅ **Полной observability** (structlog, Prometheus, OpenTelemetry)

**Основная область для улучшения:**
⚠️ **Dependency Injection** (12 нарушений) — исправление поднимет балл с 8.52 до ~9.0

**Рекомендация:** Начать с Фазы 0 (R0.1-R0.3), которая займёт 3-4 часа и устранит все критические DI нарушения.

---

*Документ подготовлен на основе deep dive анализа кодовой базы BioETL v5.2*
*Дата аудита: 2025-12-23*
