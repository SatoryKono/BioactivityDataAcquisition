# ADR-020: Декомпозиция BasePipeline

**Status:** Accepted (Implemented 2025-12-16)
**Date:** 2025-12-16
**Decision makers:** @BioETL-Team

## Контекст

### Проблема

`BasePipeline` являлся God Object с 13+ зависимостями в конструкторе:

```python
# СТАРЫЙ API (deprecated)
def __init__(
    self,
    pipeline_name: str,
    provider: str,
    entity_type: str,
    run_type: RunType,
    data_source: DataSourcePort,
    storage: StoragePort,
    lock: LockPort,
    checkpoint: CheckpointPort,
    quarantine: QuarantinePort,
    logger: LoggerPort,
    metrics: MetricsPort,
    resume: bool = False,
    limit: int | None = None,
) -> None
```

### Выявленные проблемы

1. **God Object Anti-pattern**: 13 параметров конструктора смешивают конфигурацию, runtime параметры и I/O порты

2. **Риск циклических зависимостей**: сборка менеджеров внутри `BasePipeline`
   приводит к self-ссылкам (менеджеры получают `pipeline` целиком)

3. **Нарушение SRP**: Класс отвечает за хранение конфигурации И координацию выполнения

4. **Сложность тестирования**: Требуется мокать все 13 зависимостей для unit-тестов

5. **Отсутствие lifecycle management**: Нет централизованного механизма закрытия I/O ресурсов

### Затронутые файлы

- `src/bioetl/application/core/base.py` - основной класс
- `src/bioetl/domain/config.py` - **NEW**
- `src/bioetl/application/core/pipeline_services.py` - **NEW**
- `src/bioetl/application/pipelines/chembl/activity.py` - наследник
- `src/bioetl/application/core/runner.py` - зависит от BasePipeline
- `src/bioetl/application/core/batch_executor.py` - зависит от BasePipeline
- `src/bioetl/application/core/lock_manager.py` - зависит от BasePipeline
- `src/bioetl/application/core/quarantine_manager.py` - зависит от BasePipeline
- `tests/unit/application/test_base_pipeline.py` - тесты
- `tests/unit/application/core/test_batch_executor.py` - тесты
- `tests/unit/application/test_pipeline_config.py` - тесты
- `tests/unit/application/pipelines/test_chembl_activity_unit.py` - тесты

## Решение

### 1. Разделить на три структуры

#### PipelineConfig (immutable dataclass)

```python
@dataclass(frozen=True)
class PipelineConfig:
    """Static pipeline configuration."""
    pipeline_name: str
    provider: str
    entity_type: str
    primary_keys: list[str]
    silver_table: str
    gold_table: str | None = None
    batch_size: int = 100
    checkpoint_interval: int = 1000
```

#### RuntimeConfig (immutable dataclass)

```python
@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime execution parameters."""
    run_type: RunType
    resume: bool = False
    limit: int | None = None
    skip_gold: bool = False  # Skip Gold writes (composite sub-pipelines)
```

#### PipelineServices (immutable dataclass with lifecycle)

```python
@dataclass(frozen=True)
class PipelineServices:
    """I/O port dependencies with lifecycle management."""
    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort

    async def aclose(self) -> None:
        """Gracefully close all I/O resources."""
        results = await asyncio.gather(
            self.data_source.aclose(),
            self.storage.aclose(),
            self.lock.aclose(),
            self.checkpoint.aclose(),
            self.quarantine.aclose(),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                self.logger.error("Error during shutdown", error=result)
```

### 2. Рефакторинг BasePipeline

```python
class BasePipeline(ABC):
    """Refactored pipeline with decomposed dependencies."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run_id: RunID,
        transformer: BaseTransformer | None = None,
    ) -> None:
        self._config = config
        self._runtime = runtime
        self._services = services
        self._run_id = run_id
        self._transformer = transformer
        # ... lazy-initialized components
```

### 3. Устранение циклических зависимостей

Сборка вынесена в composition layer: `PipelineRunner` получает зависимости
через явный DI и не создаётся внутри `BasePipeline`.

```python
# Вместо:
self.runner = PipelineRunner(self)  # circular ref!

# Стало:
pipeline = ChEMBLActivityPipeline.create(
    run_id=run_id,
    runtime=runtime,
    services=services,
    config=config,
    transformer=transformer,
)
runner = PipelineRunner(
    config=pipeline.config,
    runtime=pipeline.runtime,
    services=pipeline.services,
    context=pipeline.context,
    executor=batch_executor,
    checkpoint_manager=checkpoint_manager,
    shutdown_signal=pipeline.shutdown_signal,
    logger=logger,
    lock_manager=lock_manager,
    preflight=preflight,
    postrun=postrun,
    lifecycle_service=lifecycle_service,
    observer=observer,
    pipeline=pipeline,
    tracer=tracer,
)
```

### 4. Resource Lifecycle Management

Graceful shutdown реализован в `PipelineRunner.run()` через контекстные
менеджеры и `finally`-cleanup:

```python
try:
    with self._observer:
        async with self._services, self._lock_manager:
            ...
finally:
    await self._postrun_service.cleanup(self._tracer)
```

## Последствия

### Положительные

1. **Ясное разделение ответственности**: Config, Runtime, Services - три чётких категории
2. **Улучшенная тестируемость**: Можно мокать только нужные части
3. **Устранение циклических зависимостей**: Менеджеры не ссылаются на весь pipeline
4. **Иммутабельность конфигурации**: Все dataclass frozen
5. **Переиспользование**: `PipelineServices` можно шарить между пайплайнами
6. **Lifecycle management**: Централизованное закрытие I/O ресурсов через `aclose()`

### Отрицательные

1. **Breaking change**: Требуется миграция всех наследников `BasePipeline`
2. **Рефакторинг тестов**: Нужно обновить test fixtures

### Риски

| Риск                | Митигация                             | Статус |
|---------------------|---------------------------------------|--------|
| Пропуск зависимости | Dependency map + полный тест coverage | Закрыт |
| Регрессии           | Baseline metrics + integration tests  | Закрыт |
| Resource leaks      | `PipelineServices.aclose()` в finally | Закрыт |

## План миграции

### Фаза 1: Подготовка

- [x] Карта зависимостей
- [x] ADR документ
- [x] Baseline метрики

### Фаза 2: Создание структур

- [x] `PipelineConfig` dataclass
- [x] `RuntimeConfig` dataclass
- [x] `PipelineServices` dataclass с `aclose()`

### Фаза 3: Рефакторинг BasePipeline

- [x] Новый конструктор `__init__(config, runtime, services)`
- [x] Обновление менеджеров (`from_components()`)
- [x] Lazy initialization компонентов
- [x] `ShutdownSignal` для graceful shutdown

### Фаза 4: Миграция наследников

- [x] `ChEMBLActivityPipeline` (использует `create()` factory)
- [ ] Будущие пайплайны

### Фаза 5: Обновление тестов

- [x] `test_base_pipeline.py`
- [x] `test_batch_executor.py`
- [x] `test_chembl_activity_unit.py`

### Фаза 6: Удаление shim

- [x] Удалить `from_params()`
- [x] Финальное обновление документации

## Альтернативы рассмотренные

### 1. Builder Pattern

- **Плюсы**: Fluent API
- **Минусы**: Больше кода, неявные зависимости
- **Решение**: Отклонено

### 2. Factory + DI Container

- **Плюсы**: Полная инверсия зависимостей
- **Минусы**: Over-engineering для текущего масштаба
- **Решение**: Отклонено, рассмотреть позже

### 3. Оставить как есть

- **Плюсы**: Нет breaking changes
- **Минусы**: Технический долг растёт
- **Решение**: Отклонено

## Диаграмма архитектуры (после рефакторинга)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BasePipeline                                │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ PipelineConfig │  │ PipelineRuntime  │  │  PipelineServices  │  │
│  │   (frozen)     │  │    Config        │  │    (frozen)        │  │
│  │                │  │   (frozen)       │  │                    │  │
│  │ - pipeline_name│  │ - run_type       │  │ - data_source      │  │
│  │ - provider     │  │ - resume         │  │ - storage          │  │
│  │ - entity_type  │  │ - limit          │  │ - lock             │  │
│  │ - primary_keys │  │                  │  │ - checkpoint       │  │
│  │ - silver_table │  │                  │  │ - quarantine       │  │
│  │ - batch_size   │  │                  │  │ - metrics          │  │
│  │                │  │                  │  │ - logger           │  │
│  │                │  │                  │  │                    │  │
│  │                │  │                  │  │ + aclose()         │  │
│  └────────────────┘  └──────────────────┘  └────────────────────┘  │
│                                                                      │
│  Lazy-initialized (no circular refs):                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Orchestrator │  │   Executor   │  │   CheckpointManager      │  │
│  │.from_components│ │.from_components│ │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ChEMBLActivityPipeline
                    (uses CHEMBL_ACTIVITY_CONFIG)
```

## Related ADRs

- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — assembles decomposed components
- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports — LoggerPort in PipelineServices
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — PipelineServices design
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates — further domain layer improvements

## Связанные документы

- `docs/refactoring/basepipeline-dependency-map.md`
- `docs/refactoring/entry-criteria-check.md`
- `RULES.md` Section 1.1 (Ports & Adapters)
