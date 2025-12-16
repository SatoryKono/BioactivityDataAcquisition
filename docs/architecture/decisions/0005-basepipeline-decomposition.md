# ADR-0005: Декомпозиция BasePipeline

## Статус

Принято

## Дата

2025-12-16

## Контекст

### Проблема

`BasePipeline` является God Object с 13+ зависимостями в конструкторе:

```python
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
    logger: BoundLogger,
    metrics: MetricsPort,
    resume: bool = False,
    limit: int | None = None,
) -> None
```

### Выявленные проблемы

1. **God Object Anti-pattern**: 13 параметров конструктора смешивают конфигурацию, runtime параметры и I/O порты

2. **Циклические зависимости**: `BasePipeline` создаёт менеджеры (`PipelineOrchestrator`, `PipelineExecutor`, `LockManager`, `QuarantineManager`), которые хранят ссылку на `self`

3. **Нарушение SRP**: Класс отвечает за хранение конфигурации И координацию выполнения

4. **Сложность тестирования**: Требуется мокать все 13 зависимостей для unit-тестов

### Затронутые файлы

- `src/bioetl/application/core/base.py` - основной класс
- `src/bioetl/application/pipelines/chembl_activity.py` - наследник
- `src/bioetl/application/core/orchestrator.py` - зависит от BasePipeline
- `src/bioetl/application/core/executor.py` - зависит от BasePipeline
- `src/bioetl/application/core/lock_manager.py` - зависит от BasePipeline
- `src/bioetl/application/core/quarantine_manager.py` - зависит от BasePipeline
- `tests/unit/application/test_base_pipeline.py` - тесты
- `tests/unit/application/test_pipeline_executor.py` - тесты

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
```

#### PipelineRuntime (dataclass)
```python
@dataclass
class PipelineRuntime:
    """Runtime execution parameters."""
    run_id: RunID
    run_type: RunType
    resume: bool = False
    limit: int | None = None
    watermark: Watermark | None = None
```

#### PipelineServices (dataclass)
```python
@dataclass
class PipelineServices:
    """I/O port dependencies."""
    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    logger: BoundLogger
```

### 2. Рефакторинг BasePipeline

```python
class BasePipeline(ABC):
    """Refactored pipeline with decomposed dependencies."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntime,
        services: PipelineServices,
    ) -> None:
        self.config = config
        self.runtime = runtime
        self.services = services
        self.context = PipelineContext(
            run_id=runtime.run_id,
            run_type=runtime.run_type,
            logger=services.logger,
        )
```

### 3. Устранение циклических зависимостей

Менеджеры будут получать только необходимые зависимости:

```python
# Вместо:
self.orchestrator = PipelineOrchestrator(self)

# Станет:
self.orchestrator = PipelineOrchestrator(
    config=self.config,
    runtime=self.runtime,
    executor=self.executor,
    lock_manager=self.lock_manager,
)
```

### 4. Compatibility Shim (14 дней)

```python
class BasePipeline(ABC):
    @classmethod
    def from_legacy(
        cls,
        pipeline_name: str,
        provider: str,
        # ... все старые параметры
    ) -> "BasePipeline":
        """DEPRECATED: Use __init__(config, runtime, services) instead.

        Will be removed after 2025-01-01.
        """
        warnings.warn(
            "BasePipeline.from_legacy() is deprecated. "
            "Use BasePipeline(config, runtime, services) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        config = PipelineConfig(...)
        runtime = PipelineRuntime(...)
        services = PipelineServices(...)
        return cls(config, runtime, services)
```

## Последствия

### Положительные

1. **Ясное разделение ответственности**: Config, Runtime, Services - три чётких категории
2. **Улучшенная тестируемость**: Можно мокать только нужные части
3. **Устранение циклических зависимостей**: Менеджеры не ссылаются на весь pipeline
4. **Иммутабельность конфигурации**: `PipelineConfig` frozen dataclass
5. **Переиспользование**: `PipelineServices` можно шарить между пайплайнами

### Отрицательные

1. **Breaking change**: Требуется миграция всех наследников `BasePipeline`
2. **Временная сложность**: Два API существуют параллельно 14 дней
3. **Рефакторинг тестов**: Нужно обновить test fixtures

### Риски

| Риск | Митигация |
|------|-----------|
| Пропуск зависимости | Dependency map + полный тест coverage |
| Регрессии | Baseline metrics + integration tests |
| Долгая миграция | Compatibility shim с deadline |

## План миграции

### Фаза 1: Подготовка (1 день)
- [x] Карта зависимостей
- [x] ADR документ
- [ ] Baseline метрики

### Фаза 2: Создание структур (1 день)
- [ ] `PipelineConfig` dataclass
- [ ] `PipelineRuntime` dataclass
- [ ] `PipelineServices` dataclass

### Фаза 3: Рефакторинг BasePipeline (2 дня)
- [ ] Новый конструктор
- [ ] Compatibility shim `from_legacy()`
- [ ] Обновление менеджеров

### Фаза 4: Миграция наследников (1 день)
- [ ] `ChEMBLActivityPipeline`
- [ ] Будущие пайплайны

### Фаза 5: Удаление shim (после 14 дней)
- [ ] Удалить `from_legacy()`
- [ ] Обновить документацию

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

## Связанные документы

- `docs/refactoring/basepipeline-dependency-map.md`
- `RULES.md` Section 1.1 (Ports & Adapters)
