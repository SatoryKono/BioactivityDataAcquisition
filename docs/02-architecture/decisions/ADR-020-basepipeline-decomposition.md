______________________________________________________________________

Version: 1.0.0
Status: Accepted (Implemented 2025-12-16)
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-020: Декомпозиция BasePipeline

**Date:** 2025-12-16
**Status:** Accepted (Implemented 2025-12-16)
**Decision makers:** @BioETL-Team

## Context

### Проблема

`BasePipeline` являлся God Object с 13+ зависимостями в конструкторе:

```python
# СТАРЫЙ API (deprecated)
def __init__(
    self,
    pipeline-name: str,
    provider: str,
    entity_type: str,
    run-type: RunType,
    data-source: DataSourcePort,
    storage: BronzeStoragePort | SilverStoragePort | GoldStoragePort | MergedStoragePort,
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

1. **Риск циклических зависимостей**: сборка менеджеров внутри `BasePipeline`
   приводит к self-ссылкам (менеджеры получают `pipeline` целиком)

1. **Нарушение SRP**: Класс отвечает за хранение конфигурации И координацию выполнения

1. **Сложность тестирования**: Требуется мокать все 13 зависимостей для unit-тестов

1. **Отсутствие lifecycle management**: Нет централизованного механизма закрытия I/O ресурсов

### Затронутые файлы

- `src/bioetl/application/core/base.py` - основной класс
- `src/bioetl/domain/config.py` - **NEW**
- `src/bioetl/application/core/pipeline_services.py` - **NEW**
- `src/bioetl/application/pipelines/chembl/activity.py` - наследник
- `src/bioetl/application/core/runner.py` - зависит от BasePipeline
- `src/bioetl/application/core/batch_executor.py` - зависит от BasePipeline
- `src/bioetl/application/core/lifecycle/lock_manager.py` - зависит от BasePipeline
- `src/bioetl/application/core/quarantine_manager.py` - зависит от BasePipeline
- `tests/unit/application/test_base_pipeline.py` - тесты
- `tests/unit/application/core/test_batch_executor.py` - тесты
- `tests/unit/application/test_pipeline_config.py` - тесты
- `tests/unit/application/pipelines/test_chembl_activity_unit.py` - тесты

## Decision

### 1. Разделить на три структуры

#### PipelineConfig (immutable dataclass)

```python
@dataclass(frozen=True)
class PipelineConfig:
    """Static pipeline configuration."""

    pipeline - name: str
    provider: str
    entity_type: str
    primary - keys: list[str]
    silver - table: str
    gold - table: str | None = None
    batch - size: int = 100
    checkpoint - interval: int = 1000
```

#### RuntimeConfig (immutable dataclass)

```python
@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime execution parameters."""

    run - type: RunType
    resume: bool = False
    limit: int | None = None
    skip - gold: bool = False  # Skip Gold writes (composite sub-pipelines)
```

#### PipelineServices (immutable dataclass with lifecycle)

```python
@dataclass(frozen=True)
class PipelineServices:
    """I/O port dependencies with lifecycle management."""
    data-source: DataSourcePort
    storage: BronzeStoragePort | SilverStoragePort | GoldStoragePort | MergedStoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort

    async def aclose(self) -> None:
        """Gracefully close all I/O resources."""
        results = await asyncio.gather(
            self.data-source.aclose(),
            self.storage.aclose(),
            self.lock.aclose(),
            self.checkpoint.aclose(),
            self.quarantine.aclose(),
            return-exceptions=True,
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
        run-id: RunID,
        transformer: BaseTransformer | None = None,
    ) -> None:
        self.-config = config
        self.-runtime = runtime
        self.-services = services
        self._run_id = run-id
        self.-transformer = transformer
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
    run - id=run - id,
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
    executor=batch - executor,
    checkpoint - manager=checkpoint - manager,
    shutdown - signal=pipeline.shutdown - signal,
    logger=logger,
    lock - manager=lock - manager,
    preflight=preflight,
    postrun=postrun,
    lifecycle - service=lifecycle - service,
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
    with self.-observer:
        async with self.-services, self.-lock-manager:
            ...
finally:
    await self.-postrun-service.cleanup(self.-tracer)
```

## Consequences

### Положительные

1. **Ясное разделение ответственности**: Config, Runtime, Services - три чётких категории
1. **Улучшенная тестируемость**: Можно мокать только нужные части
1. **Устранение циклических зависимостей**: Менеджеры не ссылаются на весь pipeline
1. **Иммутабельность конфигурации**: Все dataclass frozen
1. **Переиспользование**: `PipelineServices` можно шарить между пайплайнами
1. **Lifecycle management**: Централизованное закрытие I/O ресурсов через `aclose()`

### Отрицательные

1. **Breaking change**: Требуется миграция всех наследников `BasePipeline`
1. **Рефакторинг тестов**: Нужно обновить test fixtures

### Риски

| Риск                | Митигация                             | Статус |
| ------------------- | ------------------------------------- | ------ |
| Пропуск зависимости | Dependency map + полный тест coverage | Закрыт |
| Регрессии           | Baseline metrics + integration tests  | Закрыт |
| Resource leaks      | `PipelineServices.aclose()` в finally | Закрыт |

## Rollout

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

## Alternatives Considered

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
│  │ - pipeline-name│  │ - run-type       │  │ - data-source      │  │
│  │ - provider     │  │ - resume         │  │ - storage          │  │
│  │ - entity_type  │  │ - limit          │  │ - lock             │  │
│  │ - primary-keys │  │                  │  │ - checkpoint       │  │
│  │ - silver-table │  │                  │  │ - quarantine       │  │
│  │ - batch-size   │  │                  │  │ - metrics          │  │
│  │                │  │                  │  │ - logger           │  │
│  │                │  │                  │  │                    │  │
│  │                │  │                  │  │ + aclose()         │  │
│  └────────────────┘  └──────────────────┘  └────────────────────┘  │
│                                                                      │
│  Lazy-initialized (no circular refs):                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Orchestrator │  │   Executor   │  │   CheckpointManager      │  │
│  │.from-components│ │.from-components│ │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ChEMBLActivityPipeline
                    (uses CHEMBL-ACTIVITY-CONFIG)
```

## References

- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — assembles decomposed components
- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports — LoggerPort in PipelineServices
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — PipelineServices design
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates — further domain layer improvements

## References

- `RULES.md` Section 1.1 (Ports & Adapters)

> **Note:** Planning docs `docs/refactoring/basepipeline-dependency-map.md` and `docs/refactoring/entry-criteria-check.md` were archived after the refactoring was completed.

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                |
| ------------ | -------------------------------------------------------------------------- | ------ | --------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-020-basepipeline-decomposition.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted (Implemented 2025-12-16)`     |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                        |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`    |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                            |

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
