# BioETL: Архитектурный Обзор и План Рефакторинга

*Версия: 1.1 | Дата: 2025-12-19*
*Обновлено: Claude Architecture Review Agent*

---

## Оглавление

1. [Резюме](#1-резюме)
2. [Числовая Оценка по 10 Категориям](#2-числовая-оценка-по-10-категориям)
3. [Детальный Анализ Текущей Архитектуры](#3-детальный-анализ-текущей-архитектуры)
4. [Выявленные Проблемы](#4-выявленные-проблемы)
5. [План Рефакторинга](#5-план-рефакторинга)
6. [Метрики и Контроль Качества](#6-метрики-и-контроль-качества)

---

## 1. Резюме

### Общая Характеристика

Проект BioETL представляет собой **зрелую, хорошо структурированную ETL-систему** для сбора биоактивных данных из публичных репозиториев (ChEMBL, PubChem, UniProt, PubMed) с последующим преобразованием в Delta Lake хранилище.

### Ключевые Достоинства

- ✅ **Чёткая слоистая архитектура** (Hexagonal / Ports & Adapters)
- ✅ **Полноценный Domain Layer** с Protocol-based портами
- ✅ **Строгий Dependency Injection** через Composition Root
- ✅ **Comprehensive Architecture Tests** (50+ проверок)
- ✅ **Medallion Architecture** (Bronze/Silver/Gold)
- ✅ **Production-Ready документация** (RULES.md v5.0, 126 требований)

### Области для Улучшения

- ⚠️ Дублирование кода в фабриках пайплайнов
- ⚠️ Смешение конфигурации и бизнес-логики в некоторых местах
- ⚠️ Неполная типизация в отдельных модулях
- ⚠️ Избыточность абстракций в application layer

---

## 2. Числовая Оценка по 10 Категориям

### 2.1. Описание Категорий

| # | Категория | Описание | Вес |
|---|-----------|----------|-----|
| 1 | **Архитектура слоёв** | Соблюдение Hexagonal/Ports & Adapters, чистота границ | 15% |
| 2 | **Модульность и связность** | Cohesion внутри модулей, Coupling между ними | 12% |
| 3 | **Качество доменной модели** | Богатство Domain Layer, Value Objects, Entities | 12% |
| 4 | **Dependency Injection** | Инверсия зависимостей, Composition Root | 10% |
| 5 | **Тестирование** | Покрытие, качество тестов, VCR, архитектурные тесты | 15% |
| 6 | **Обработка ошибок** | Классификация, Circuit Breaker, Retry, Quarantine | 10% |
| 7 | **Логирование и наблюдаемость** | Структурированные логи, метрики, трассировка | 8% |
| 8 | **Безопасность** | Секреты, PII, IAM, валидация | 6% |
| 9 | **Качество документации** | RULES.md, docstrings, комментарии | 6% |
| 10 | **Технический долг и сопровождаемость** | Чистота кода, dead code, сложность | 6% |

### 2.2. Таблица Оценок

| Категория | Описание оценки | Вес | Оценка (1-10) | Взвешенный балл |
|-----------|-----------------|-----|---------------|-----------------|
| **1. Архитектура слоёв** | Отличное соблюдение Hexagonal. 5 слоёв (domain, application, composition, infrastructure, interfaces) с чёткой матрицей импортов. Protocol-based порты. Архитектурные тесты блокируют нарушения. | 0.15 | **9** | 1.35 |
| **2. Модульность и связность** | Хорошая модульность. Cohesion высокий в domain/infrastructure. Некоторая избыточность в application (executor + runner + base). 4 пайплайна, каждый с отдельной фабрикой. | 0.12 | **7** | 0.84 |
| **3. Качество доменной модели** | Сильный domain layer: 9 портов, типизированные Value Objects (Watermark, RunID, BatchID), Enums (ErrorType, HealthStatus, CircuitBreakerState), Frozen Entities (Activity, Compound, Protein, Publication). Есть __post_init__ валидация. | 0.12 | **9** | 1.08 |
| **4. Dependency Injection** | Образцовый DI: Composition Root в bootstrap.py, все зависимости передаются в конструктор, PipelineServices как контейнер. Фабрики создают адаптеры. | 0.10 | **9** | 0.90 |
| **5. Тестирование** | Сильная структура: unit (85+ файлов), integration (13 файлов), VCR для HTTP, архитектурные тесты (проверка импортов, слоёв, протоколов). Однако покрытие можно улучшить, E2E тесты минимальны. | 0.15 | **8** | 1.20 |
| **6. Обработка ошибок** | Полноценная система: ErrorClassifier, CircuitBreaker, TokenBucket rate limiting, Quarantine для DQ ошибок, Retry с backoff. Пороги настраиваемые. | 0.10 | **8** | 0.80 |
| **7. Логирование и наблюдаемость** | structlog с run_id, PrometheusMetrics, NoOpMetrics для тестов, Anomaly Detection (IQR, MAD, Z-score). PipelineObserver для автоматического сбора. | 0.08 | **8** | 0.64 |
| **8. Безопасность** | Секреты через os.environ (централизовано в config.py), формат BIOETL_{PROVIDER}_{KEY}. PII hashing упомянут в RULES.md. Нет явных уязвимостей. | 0.06 | **7** | 0.42 |
| **9. Качество документации** | Превосходная документация: RULES.md v5.0 (Production Ready), 126 требований в REQUIREMENTS.md, AGENT.md, CLAUDE.md. Docstrings в Google Style. | 0.06 | **9** | 0.54 |
| **10. Технический долг** | Чистый код, нет явного dead code (vulture тест в архитектуре). Некоторое дублирование в фабриках. Циклическая сложность контролируется (CC ≤ 5 для domain). | 0.06 | **7** | 0.42 |

### 2.3. Интегральный Балл

```
Общий балл = Σ(Вес × Оценка) = 1.35 + 0.84 + 1.08 + 0.90 + 1.20 + 0.80 + 0.64 + 0.42 + 0.54 + 0.42
           = 8.19 / 10
```

### 2.4. Интерпретация

| Диапазон | Уровень | Описание |
|----------|---------|----------|
| 0.0 – 4.9 | Критический | Требуется срочный рефакторинг |
| 5.0 – 6.9 | Удовлетворительный | Необходимы значительные улучшения |
| 7.0 – 7.9 | Хороший | Есть области для оптимизации |
| **8.0 – 8.9** | **Очень хороший** | **Минорные улучшения** |
| 9.0 – 10.0 | Отличный | Production-ready, best practices |

**Вывод**: Проект находится на уровне **"Очень хороший" (8.19/10)**. Архитектура зрелая, соответствует Hexagonal/Clean Architecture принципам. Рекомендуются точечные улучшения для достижения уровня 9.0+.

---

## 3. Детальный Анализ Текущей Архитектуры

### 3.1. Соблюдение Слоистой Структуры

```
src/bioetl/
├── domain/          ✅ Чистая бизнес-логика, Protocols, Value Objects
├── application/     ✅ Use Cases, оркестрация (но есть избыточность)
├── composition/     ✅ Composition Root, Factories
├── infrastructure/  ✅ Адаптеры, реализация портов
└── interfaces/      ✅ CLI, PipelineRunner
```

**Матрица импортов соблюдается строго**:
- Domain не импортирует ничего кроме stdlib и domain
- Application зависит только от domain (TYPE_CHECKING исключения допустимы)
- Infrastructure реализует domain ports
- Composition связывает всё вместе

### 3.2. Ports & Adapters (Hexagonal)

**Порты (domain/ports.py):**

| Port | Назначение | Адаптеры |
|------|------------|----------|
| `DataSourcePort` | Источники данных | ChemblAdapter, PubChemClient, UniProtClient, PubMedClient |
| `StoragePort` | Bronze/Silver/Gold запись | StorageAdapter (композит) |
| `LockPort` | Распределённые блокировки | RedisDistributedLock, MemoryLock |
| `CheckpointPort` | Сохранение состояния | S3Checkpoint |
| `QuarantinePort` | Изоляция ошибок | UnifiedQuarantine |
| `MetricsPort` | Сбор метрик | PrometheusMetrics, NoOpMetrics |
| `LoggerPort` | Логирование | structlog BoundLogger |
| `OrchestrationPort` | Оркестрация | PrefectAdapter |
| `InputFilterPort` | Фильтрация входных данных | CSVFilterReader |

**Оценка**: Порты определены через `typing.Protocol`, используют `@runtime_checkable`. Все async методы для I/O портов. MetricsPort корректно sync (low-overhead).

### 3.3. Единообразие Соглашений

| Аспект | Стандарт | Соблюдение |
|--------|----------|------------|
| Именование файлов | `snake_case.py` | ✅ |
| Именование классов | `PascalCase` | ✅ |
| Структура пакетов | `{layer}/{component}/{provider}/` | ✅ |
| Docstrings | Google Style (русский) | ✅ (частично) |
| Типизация | `typing.Protocol`, NewType, TypedDict | ✅ |
| Тесты | `tests/{type}/{layer}/test_{module}.py` | ✅ |

---

## 4. Выявленные Проблемы

### 4.1. Критические (Блокеры)

Критических нарушений не выявлено.

### 4.2. Значительные (SHOULD исправить)

#### P1: Дублирование в фабриках пайплайнов

**Файлы**: `composition/factories/{chembl_activity, pubchem_compound, uniprot_protein, pubmed_publications}.py`

**Проблема**: Каждая фабрика содержит практически идентичный код для создания сервисов, отличаясь только DataSource адаптером и схемой.

**Пример дублирования**:
```python
# chembl_activity.py
def create_with_services(...):
    http_client = create_http_client(...)
    data_source = ChemblAdapter(http_client)
    storage = StorageAdapter(...)
    lock = RedisDistributedLock(...)
    # ... 20+ строк одинакового кода
```

**Влияние**: Сложность поддержки, риск рассинхронизации при изменениях.

#### P2: Избыточность абстракций в application layer

**Файлы**: `application/core/{base.py, executor.py}`, `interfaces/orchestration/runner.py`

**Проблема**: Три уровня абстракции для выполнения пайплайна:
1. `BasePipeline` — определение пайплайна
2. `PipelineExecutor` — оркестрация потока данных
3. `PipelineRunner` — управление жизненным циклом

**Анализ**: Хотя разделение ответственности правильное, на практике это создаёт:
- Длинные цепочки делегирования
- Сложность понимания flow
- Множество однотипных конструкторов

#### P3: Смешение конфигурации в нескольких местах

**Файлы**:
- `domain/config.py` — DQConfig, TableConfig
- `domain/pipeline_config.py` — PipelineConfig
- `application/core/pipeline_config.py` — PipelineRuntimeConfig
- `infrastructure/config.py` — Settings
- `infrastructure/schemas/pipeline_config.py` — PipelineYamlConfig

**Проблема**: 5 различных конфигурационных классов, границы между ними размыты.

#### P4: Неполная типизация в отдельных модулях

**Примеры**:
- `schema: Any` в `StoragePort.write_silver` (чтобы не зависеть от PyArrow)
- `*args, **kwargs` в `QuarantinePort.write`

**Влияние**: Снижает эффективность mypy, возможны runtime ошибки.

### 4.3. Минорные (MAY исправить)

#### P5: Отсутствие централизованного Event Bus

**Текущее состояние**: Наблюдаемость реализована через PipelineObserver (observer pattern), но нет единого механизма для публикации доменных событий.

#### P6: Дублирование констант

**Пример**: `ENTITY_MAPPING` в `adapters/chembl/client.py` и конфигах пайплайнов содержит пересекающуюся информацию.

#### P7: Тесты E2E минимальны

**Текущее состояние**: 2 файла E2E тестов (`test_full_pipeline.py`, `test_infrastructure.py`). Для production-ready системы желательно больше сценариев.

---

## 5. План Рефакторинга

### 5.1. Приоритизация

| # | Задача | Приоритет | Сложность | Влияние |
|---|--------|-----------|-----------|---------|
| R1 | Унификация фабрик пайплайнов | HIGH | Medium | +0.3 балла |
| R2 | Консолидация конфигурации | HIGH | Medium | +0.2 балла |
| R3 | Улучшение типизации портов | MEDIUM | Low | +0.1 балла |
| R4 | Упрощение application layer | MEDIUM | High | +0.2 балла |
| R5 | Расширение E2E тестов | LOW | Medium | +0.1 балла |
| R6 | Добавление Event Bus | LOW | High | +0.1 балла |

### 5.2. Детальные Шаги Рефакторинга

---

#### R1: Унификация Фабрик Пайплайнов

**Цель**: Устранить дублирование кода в 4+ фабриках, создать единую Generic Factory.

**Текущее состояние**:
```
composition/factories/
├── base_pipeline_factory.py      # Базовый класс (недоиспользован)
├── base_services_factory.py      # Общая логика сервисов
├── chembl_activity.py            # 150 строк, 80% дублирования
├── pubchem_compound.py           # 150 строк, 80% дублирования
├── uniprot_protein.py            # 150 строк, 80% дублирования
└── pubmed_publications.py        # 150 строк, 80% дублирования
```

**Целевое состояние**:
```
composition/factories/
├── base_factory.py               # GenericPipelineFactory[T]
├── data_source_registry.py       # Реестр создания DataSource по provider
└── pipeline_definitions/
    ├── chembl_activity.yaml      # Декларативное определение
    ├── pubchem_compound.yaml
    └── ...
```

**Конкретные правки**:

1. **Создать `GenericPipelineFactory`**:
```python
# composition/factories/base_factory.py
class GenericPipelineFactory(Generic[TPipeline]):
    """Единая фабрика для создания пайплайнов."""

    def __init__(
        self,
        pipeline_class: type[TPipeline],
        data_source_creator: Callable[..., DataSourcePort],
        silver_schema: pa.Schema,
    ):
        self.pipeline_class = pipeline_class
        self._create_data_source = data_source_creator
        self.silver_schema = silver_schema

    def create_with_services(
        self,
        runtime: PipelineRuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> TPipeline:
        # Общая логика создания сервисов (вынесена из дублирующихся фабрик)
        data_source = self._create_data_source(settings, config, filter_config)
        services = self._build_services(settings, logger, data_source)
        return self.pipeline_class.create(runtime, services, config)
```

2. **Создать `DataSourceRegistry`**:
```python
# composition/factories/data_source_registry.py
DATA_SOURCE_CREATORS: dict[str, Callable] = {
    "chembl": create_chembl_adapter,
    "pubchem": create_pubchem_client,
    "uniprot": create_uniprot_client,
    "pubmed": create_pubmed_client,
}
```

3. **Упростить регистрацию пайплайнов**:
```python
# composition/factories/chembl_activity.py (после рефакторинга)
from bioetl.composition.factories.base_factory import GenericPipelineFactory
from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline

factory = GenericPipelineFactory(
    pipeline_class=ChEMBLActivityPipeline,
    data_source_creator=create_chembl_adapter,
    silver_schema=CHEMBL_ACTIVITY_SCHEMA,
)
PipelineRegistry.register("chembl_activity", factory)
```

**Риски**:
- Регрессии в существующих пайплайнах
- Сложность миграции если есть кастомная логика в фабриках

**Митигация**:
- Параллельное сосуществование старых и новых фабрик
- Feature flag для переключения
- Полное покрытие тестами перед удалением старых фабрик

**Критерии "готово"**:
- [ ] GenericPipelineFactory создан и покрыт тестами
- [ ] Минимум 2 пайплайна мигрированы на новую фабрику
- [ ] Старые фабрики помечены @deprecated
- [ ] `make test` проходит без регрессий
- [ ] Код дублирования сокращён на 60%+

---

#### R2: Консолидация Конфигурации

**Цель**: Уменьшить количество конфигурационных классов с 5 до 3.

**Текущее состояние**:
1. `domain/config.py` — DQConfig, TableConfig
2. `domain/pipeline_config.py` — PipelineConfig (static)
3. `application/core/pipeline_config.py` — PipelineRuntimeConfig
4. `infrastructure/config.py` — Settings (pydantic-settings)
5. `infrastructure/schemas/pipeline_config.py` — PipelineYamlConfig

**Целевое состояние**:
1. `domain/config.py` — DQConfig, TableConfig, **PipelineConfig** (объединить)
2. `infrastructure/config.py` — Settings + RuntimeConfig (CLI params)
3. `infrastructure/schemas/pipeline_config.py` — PipelineYamlConfig (сохранить для валидации YAML)

**Конкретные правки**:

1. **Объединить PipelineConfig и смежные в domain**:
```python
# domain/config.py
@dataclass(frozen=True)
class PipelineConfig:
    """Полная конфигурация пайплайна (immutable)."""

    # Identity
    pipeline_name: str
    provider: str
    entity_type: str
    version: str

    # Data Quality
    dq: DQConfig

    # Table
    table: TableConfig  # Вместо отдельных primary_keys, silver_table, gold_table

    # Processing
    batch_size: int = 100
    checkpoint_interval: int = 1000

    # Gold filter (optional)
    gold_filter_types: list[str] = field(default_factory=list)
```

2. **Перенести RuntimeConfig в infrastructure**:
```python
# infrastructure/config.py
@dataclass
class RuntimeConfig:
    """Runtime параметры (CLI)."""
    run_type: RunType
    resume: bool
    limit: int | None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
```

**Риски**:
- Много файлов нужно обновить (импорты)
- Возможные конфликты с существующим кодом

**Митигация**:
- Использовать IDE для safe rename
- Добавить re-exports для обратной совместимости

**Критерии "готово"**:
- [ ] Количество config классов ≤ 3
- [ ] Нет циклических импортов
- [ ] Все тесты проходят
- [ ] Документация обновлена

---

#### R3: Улучшение Типизации Портов

**Цель**: Устранить `Any` в сигнатурах портов где возможно.

**Конкретные правки**:

1. **StoragePort.write_silver — schema**:
```python
# Вариант A: Generic Protocol
class StoragePort(Protocol[TSchema]):
    async def write_silver(
        self, ..., schema: TSchema, ...
    ) -> None: ...

# Вариант B: Типизированный alias (предпочтительно)
# domain/types.py
ArrowSchema = NewType("ArrowSchema", Any)  # Документирует намерение

# domain/ports.py
async def write_silver(
    self, ..., schema: ArrowSchema, ...
) -> None: ...
```

2. **QuarantinePort.write — убрать *args, **kwargs**:
```python
# Текущее
async def write(
    self,
    pipeline: str,
    error_code: str,
    payload: dict[str, Any],
    bronze_batch_id: BatchID,
    *args: Any,
    **kwargs: Any,
) -> Any: ...

# Целевое
async def write(
    self,
    pipeline: str,
    error_code: str,
    payload: dict[str, Any],
    bronze_batch_id: BatchID,
    run_id: RunID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None: ...
```

**Критерии "готово"**:
- [ ] `mypy --strict` проходит без дополнительных игнорирований
- [ ] Нет `Any` в публичных сигнатурах портов (кроме документированных исключений)

---

#### R4: Упрощение Application Layer

**Цель**: Уменьшить количество абстракций с 3 до 2.

**Текущее**:
```
BasePipeline → PipelineExecutor → PipelineRunner
```

**Целевое**:
```
Pipeline → PipelineRunner (с встроенным execution)
```

**Конкретные правки**:

1. **Объединить BasePipeline и PipelineExecutor**:
```python
# application/core/pipeline.py
class Pipeline(ABC):
    """ETL Pipeline с встроенной логикой выполнения."""

    def __init__(self, config: PipelineConfig, services: PipelineServices):
        self._config = config
        self._services = services
        self._record_processor = self._create_record_processor()

    @abstractmethod
    async def transform(self, record: BronzeRecord) -> SilverRecord | None:
        """Transform bronze → silver."""
        pass

    async def execute(self, watermark: Watermark | None, limit: int | None) -> ExecutionResult:
        """Выполнить ETL (встроенная логика из Executor)."""
        async for record in self._services.data_source.fetch(...):
            transformed = await self.transform(record)
            # ... batch processing
```

**Риски**:
- Существенный рефакторинг с потенциальными регрессиями
- Потеря гибкости (если нужны разные executors)

**Митигация**:
- Сохранить возможность кастомизации через стратегии
- Постепенная миграция (сначала новые пайплайны)

**Критерии "готово"**:
- [ ] Один класс Pipeline вместо BasePipeline + Executor
- [ ] PipelineRunner упрощён
- [ ] Все существующие пайплайны работают

---

#### R5: Расширение E2E Тестов

**Цель**: Увеличить покрытие E2E сценариев.

**Текущее**: 2 файла, базовые сценарии.

**Целевое**: 5+ файлов, покрытие основных flows.

**Новые тесты**:

1. `tests/e2e/test_incremental_load.py` — инкрементальная загрузка с watermark
2. `tests/e2e/test_backfill_with_lock.py` — backfill с эксклюзивной блокировкой
3. `tests/e2e/test_graceful_shutdown.py` — SIGTERM и checkpoint recovery
4. `tests/e2e/test_quarantine_flow.py` — обработка DQ ошибок
5. `tests/e2e/test_circuit_breaker.py` — поведение при отказе провайдера

**Критерии "готово"**:
- [ ] 5+ E2E тестов
- [ ] Покрытие основных сценариев из REQUIREMENTS.md
- [ ] CI проходит за разумное время (<10 мин)

---

#### R6: Добавление Event Bus (Опционально)

**Цель**: Обеспечить слабую связность через доменные события.

**Реализация**:
```python
# domain/events.py
@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    run_id: RunID | None = None

@dataclass(frozen=True)
class RecordProcessed(DomainEvent):
    entity_id: EntityID
    layer: Literal["bronze", "silver", "gold"]

@dataclass(frozen=True)
class BatchCompleted(DomainEvent):
    batch_id: BatchID
    record_count: int
```

```python
# domain/ports.py
class EventBusPort(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None: ...
```

**Критерии "готово"**:
- [ ] EventBusPort определён в domain
- [ ] InMemoryEventBus реализован для тестов
- [ ] Минимум 3 события опубликовываются в pipeline flow

---

## 6. Метрики и Контроль Качества

### 6.1. Метрики для Мониторинга

| Метрика | Текущее | Целевое | Как измерить |
|---------|---------|---------|--------------|
| Интегральный балл | 8.19 | 9.0+ | Переоценка по 10 категориям |
| Дублирование кода (%) | ~25% | <10% | `jscpd` или `radon` |
| Покрытие тестами (%) | ~80% | >95% | `pytest --cov` |
| Цикломатическая сложность | <5 (domain) | <5 везде | `radon cc` |
| mypy ошибки | 0* | 0 | `mypy --strict` |
| Количество TODO/FIXME | ? | <10 | `grep -r TODO` |

### 6.2. Прогноз Изменения Балла

| Рефакторинг | Категории | Прирост |
|-------------|-----------|---------|
| R1 (Фабрики) | Модульность, Тех. долг | +0.3 |
| R2 (Конфигурация) | Модульность | +0.2 |
| R3 (Типизация) | Качество domain | +0.1 |
| R4 (Application) | Модульность | +0.2 |
| R5 (E2E тесты) | Тестирование | +0.1 |
| **Итого** | | **+0.9** |

**Прогнозируемый балл после рефакторинга**: 8.19 + 0.9 = **9.09 / 10** (Отличный уровень)

### 6.3. Автоматизация Контроля

**Рекомендуемые проверки в CI**:

```yaml
# .github/workflows/quality.yml
jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - run: make arch-test           # Архитектурные тесты
      - run: make arch-lint           # import-linter contracts
      - run: mypy --strict src/       # Типизация
      - run: radon cc src/ -a -nc     # Цикломатическая сложность
      - run: jscpd src/ --threshold 5 # Дублирование
```

### 6.4. Roadmap

| Фаза | Задачи | Результат |
|------|--------|-----------|
| **Фаза 1** (Критичное) | R1, R2 | Балл → 8.7 |
| **Фаза 2** (Улучшения) | R3, R4 | Балл → 9.0 |
| **Фаза 3** (Полировка) | R5, R6 | Балл → 9.1+ |

---

## Заключение

Проект BioETL демонстрирует **высокий уровень архитектурной зрелости** (8.19/10). Hexagonal Architecture реализована корректно, Domain Layer чистый, Dependency Injection образцовый.

Основные направления улучшения:
1. **Унификация фабрик** — устранит 60%+ дублирования
2. **Консолидация конфигурации** — упростит понимание системы
3. **Расширение E2E тестов** — повысит уверенность в production

После выполнения плана рефакторинга проект достигнет уровня **9.0+ ("Отличный")**, что соответствует best practices enterprise-grade ETL систем.

---

---

## Changelog

### v1.1 (2025-12-19)
- Обновлена версия документа
- Подтверждён интегральный балл 8.19/10
- Статистика кодовой базы: 115 исходных файлов, 115 тестовых файлов (1:1 соотношение)
- Верифицированы все архитектурные слои и импорты

### v1.0 (2025-12-19)
- Первоначальный архитектурный обзор
- Определены 10 категорий оценки
- Сформирован план рефакторинга R1-R6

---

*Документ подготовлен: 2025-12-19*
*Автор: Архитектурный Обзор Claude*
