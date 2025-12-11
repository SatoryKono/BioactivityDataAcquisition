# План рефакторинга архитектуры BioETL

**Дата обновления:** 2025-12-11
**Интегральный балл архитектуры:** 6.15/10
**Целевой балл:** 7.2–7.5
**Статус:** В работе

---

## Оглавление

1. [Краткое резюме](#краткое-резюме)
2. [Архитектурная оценка](#архитектурная-оценка)
3. [Фаза 1: Устранение доменных прокси инфраструктуры](#фаза-1-устранение-доменных-прокси-инфраструктуры)
4. [Фаза 2: Полноценная регистрация схем и валидации](#фаза-2-полноценная-регистрация-схем-и-валидации)
5. [Фаза 3: Избавление от глобального реестра провайдеров](#фаза-3-избавление-от-глобального-реестра-провайдеров)
6. [Фаза 4: Усиление наблюдаемости и контроля качества](#фаза-4-усиление-наблюдаемости-и-контроля-качества)
7. [Метрики и тесты](#метрики-и-тесты)
8. [Порядок выполнения](#порядок-выполнения)

---

## Краткое резюме

Архитектура проекта следует принципам **Hexagonal Architecture (Ports & Adapters)** с четырьмя слоями:

```
┌─────────────────────────────────────────────────────────────┐
│                        interfaces                            │
│              (CLI, REST API, composition root)               │
├─────────────────────────────────────────────────────────────┤
│                       application                            │
│          (use cases, orchestration, pipelines)               │
├─────────────────────────────────────────────────────────────┤
│                         domain                               │
│    (entities, value objects, contracts ABC/Protocol)         │
├─────────────────────────────────────────────────────────────┤
│                      infrastructure                          │
│        (HTTP clients, files, DB, Pandera, logging)           │
└─────────────────────────────────────────────────────────────┘
```

### Текущие проблемы (приоритет ↓)

| # | Проблема | Влияние | Категория |
|---|----------|---------|-----------|
| 1 | Утечка инфраструктуры в домен через ConfigMigrator прокси | Нарушение направленности зависимостей | Слоистая архитектура |
| 2 | Регистрация схем без реальных Pandera-валидаторов (None) | Отложенная валидация, смешение ответственности | Валидация данных |
| 3 | Глобальное состояние `_PROVIDER_REGISTRY` | Скрытые зависимости, риски параллельного запуска | DI/Конфигурация |
| 4 | Неунифицированное логирование и метрики | Сложность отладки и мониторинга | Наблюдаемость |

---

## Архитектурная оценка

| Категория | Описание | Вес | Оценка | Взвешенный балл |
|-----------|----------|-----|--------|-----------------|
| Слоистая архитектура | Чёткость разделения domain/application/infrastructure | 0.15 | 7 | 1.05 |
| Ports & Adapters / DDD | Наличие портов, явность границ контекстов | 0.10 | 6 | 0.60 |
| Модульность и связность | Разбиение на модули, отсутствие циклов | 0.10 | 6 | 0.60 |
| Конфигурация и DI | Чистота инъекций, отсутствие глобального состояния | 0.10 | 5.5 | 0.55 |
| Обработка ошибок | Политики ошибок, fail-fast, дефолты | 0.10 | 6 | 0.60 |
| Логирование и наблюдаемость | Единообразие логов/метрик | 0.05 | 6 | 0.30 |
| Тестирование и QA-гейты | Архитектурные тесты, покрытие | 0.10 | 7 | 0.70 |
| Документация и стандарты | Правила и путеводители | 0.10 | 7 | 0.70 |
| Валидация данных и схемы | Полнота Pandera-схем, регистрация | 0.10 | 5 | 0.50 |
| Технический долг | Депрекейшены, обратная совместимость | 0.10 | 5.5 | 0.55 |
| **Итого** | | **1.0** | | **6.15** |

**Уровень 5–7.9:** Система функционирует, но заметен технический долг и точки риска.

---

## Фаза 1: Устранение доменных прокси инфраструктуры

**Цель:** Восстановить строгую направленность зависимостей (domain → ничего внешнего).

### Задача 1.1: Удаление ConfigMigrator прокси из домена

**Проблема:**
Файл `src/bioetl/domain/configs/migration.py` содержит динамический импорт из infrastructure через `importlib.import_module()`, что нарушает изоляцию доменного слоя даже при использовании `__getattr__` для lazy loading.

**Текущее состояние:**
```python
# src/bioetl/domain/configs/migration.py:32-34
mod = importlib.import_module(
    ".".join(["bioetl", "infrastructure", "config", "migration"])
)
return getattr(mod, "ConfigMigrator")
```

**Затронутые файлы:**

| Файл | Действие |
|------|----------|
| `src/bioetl/domain/configs/migration.py` | Удалить полностью |
| `src/bioetl/domain/configs/__init__.py:141-153` | Удалить реэкспорт ConfigMigrator |
| `tests/bioetl/domain/test_config_migration.py:6` | Импорт уже из infrastructure ✓ |
| `tests/project_rules/test_config_validation.py:10` | Импорт уже из infrastructure ✓ |

**Шаги выполнения:**

```bash
# 1. Проверить внешние зависимости на старый путь
grep -r "from bioetl.domain.configs.migration import\|from bioetl.domain.configs import ConfigMigrator" src/ tests/

# 2. Удалить deprecated модуль
rm src/bioetl/domain/configs/migration.py

# 3. Обновить __init__.py (удалить строки 141-153)
# Удалить блок:
#     if name == "ConfigMigrator":
#         ...
#         return ConfigMigrator

# 4. Запустить архитектурные тесты
pytest tests/architecture/test_domain_boundaries.py -v
```

**Критерии готовности:**
- [ ] Файл `domain/configs/migration.py` удалён
- [ ] Нет `__getattr__` для ConfigMigrator в `domain/configs/__init__.py`
- [ ] Архитектурный тест `test_domain_has_no_dynamic_infrastructure_imports` проходит
- [ ] Нет нарушений в `pytest tests/architecture/ -v`

**Риски и митигация:**
- **Риск:** Внешний код зависит от `bioetl.domain.configs.migration`
- **Митигация:** Deprecation warning уже работает; добавить Breaking Change в CHANGELOG

---

### Задача 1.2: Удаление InMemoryProviderRegistry из domain прокси

**Проблема:**
Модуль `domain/provider_registry.py` содержит `__getattr__`, который при запросе `InMemoryProviderRegistry` выбрасывает `ImportError` с указанием на infrastructure. Это допустимо, но лучше удалить прокси полностью.

**Текущее состояние:**
```python
# src/bioetl/domain/provider_registry.py:104-111
def __getattr__(name: str) -> Any:
    if name == "InMemoryProviderRegistry":
        raise ImportError(
            "InMemoryProviderRegistry is no longer available in bioetl.domain. "
            "Import it from bioetl.infrastructure.provider_registry instead."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Действие:** Оставить как есть (уже корректно предотвращает импорт).

**Критерий готовности:**
- [ ] Подтвердить, что нет реальных импортов `InMemoryProviderRegistry` из domain

```bash
grep -r "from bioetl.domain.provider_registry import InMemoryProviderRegistry\|from bioetl.domain import.*InMemoryProviderRegistry" src/ tests/
```

---

### Задача 1.3: Консолидация дублирующихся классов

**Проблема:**
Класс `InMemoryProviderRegistry` может быть продублирован в application layer.

**Проверка:**
```bash
grep -r "class InMemoryProviderRegistry" src/
```

**Ожидаемый результат:**
```
src/bioetl/infrastructure/provider_registry.py:17:class InMemoryProviderRegistry(ProviderRegistryABC):
```

Если найден дубликат в `application/memory_registry.py`:

**Шаги выполнения:**
1. Обновить все импорты на `infrastructure.provider_registry`
2. Удалить дубликат из application
3. Обновить исключения в архитектурных тестах

---

### Задача 1.4: Архитектурный тест на динамические импорты

**Статус:** ✓ Уже реализован

Тест `test_domain_has_no_dynamic_infrastructure_imports` в `tests/architecture/test_domain_boundaries.py:463-491` проверяет:

```python
def test_domain_has_no_dynamic_infrastructure_imports(
    self, domain_files: list[Path], domain_trees: dict[Path, ast.Module]
) -> None:
    """Verify domain doesn't use importlib to import infrastructure."""
    violations: list[str] = []
    for file_path in domain_files:
        code = file_path.read_text(encoding="utf-8")
        if "importlib.import_module" in code:
            for forbidden_layer in ("infrastructure", "application", "interfaces"):
                if forbidden_layer in code:
                    violations.append(...)
```

**После удаления `domain/configs/migration.py` этот тест будет проходить.**

---

## Фаза 2: Полноценная регистрация схем и валидации

**Цель:** Гарантировать валидацию на уровне инфраструктуры, оставить домен чистым от технологических деталей (Pandera).

### Задача 2.1: Анализ текущей регистрации схем

**Текущее состояние:**

```python
# src/bioetl/domain/schemas/__init__.py:37-38
for name, cols in mapping.items():
    provider.register(name, None, column_order=cols)  # schema=None!
```

Домен регистрирует только **порядок колонок** с `schema=None`, что:
- Откладывает создание реальных Pandera-схем на момент первого использования
- Смешивает ответственность: домен знает о структуре схем, но не о валидации
- Усложняет тестирование: схемы создаются лениво через `generate_schema_from_column_order()`

**Текущая архитектура:**
```
domain/schemas/
├── __init__.py          # register_schemas() - регистрирует колонки с None
├── registry.py          # SchemaRegistry - хранит schema|None + column_order
├── generator.py         # generate_schema_from_column_order() - создаёт Pandera динамически
└── chembl/
    └── output_views.py  # ACTIVITY_OUTPUT_COLUMNS и т.д.

infrastructure/validation/schemas/
├── chembl/
│   ├── activity.py      # ActivityOutputSchema(pa.DataFrameModel)
│   ├── assay.py         # AssayOutputSchema
│   └── ...
└── pandera_base.py      # BaseGeneratedColumnsModel
```

---

### Задача 2.2: Перенос регистрации Pandera-схем в инфраструктуру

**Целевая архитектура:**

```
domain/schemas/
├── registry.py          # SchemaRegistry (без изменений в контракте)
├── contracts.py         # OutputSchemaSpec - описание полей без Pandera
└── chembl/
    └── field_specs.py   # Спецификации полей (колонки + типы)

infrastructure/validation/
├── schemas/
│   └── chembl/          # Pandera DataFrameModel классы
├── registry_bootstrap.py # register_pandera_schemas() - регистрирует реальные схемы
└── factories.py          # PanderaSchemaProviderFactory
```

**Шаги выполнения:**

#### Этап 2.2.1: Создать инфраструктурный bootstrap для схем

```python
# src/bioetl/infrastructure/validation/registry_bootstrap.py
"""Bootstrap Pandera schemas into the domain registry."""

from bioetl.domain.validation import SchemaProviderABC
from bioetl.infrastructure.validation.schemas.chembl.activity import (
    ActivityOutputSchema,
)
from bioetl.infrastructure.validation.schemas.chembl.assay import AssayOutputSchema
# ... другие импорты


def register_pandera_schemas(registry: SchemaProviderABC) -> SchemaProviderABC:
    """Register actual Pandera schemas into the registry.

    This replaces None placeholders with concrete Pandera DataFrameModel classes.
    Should be called during application bootstrap, not in domain.
    """
    schema_mapping = {
        "activity_output": ActivityOutputSchema,
        "assay_output": AssayOutputSchema,
        "cell_output": CellOutputSchema,
        "molecule_output": MoleculeOutputSchema,
        "publication_output": PublicationOutputSchema,
        "target_output": TargetOutputSchema,
        "tissue_output": TissueOutputSchema,
    }

    for name, schema_class in schema_mapping.items():
        # Get existing column order from registry
        try:
            column_order = registry.get_schema_columns(name)
        except ValueError:
            column_order = None

        # Register with actual Pandera schema
        registry.register(name, schema_class, column_order=column_order)

    return registry
```

#### Этап 2.2.2: Обновить composition root для bootstrap схем

```python
# src/bioetl/interfaces/composition_root.py

def _bootstrap_schema_registry(self) -> SchemaProviderABC:
    """Bootstrap schema registry with Pandera schemas."""
    from bioetl.domain.schemas import register_schemas
    from bioetl.domain.schemas.registry import create_default_schema_registry
    from bioetl.infrastructure.validation.registry_bootstrap import (
        register_pandera_schemas,
    )

    # 1. Create empty registry
    registry = create_default_schema_registry()

    # 2. Register domain column orders
    register_schemas(registry)

    # 3. Register infrastructure Pandera schemas
    register_pandera_schemas(registry)

    return registry
```

#### Этап 2.2.3: Обновить домен для работы без None-схем (опционально)

Текущий код в `SchemaRegistry.get_schema()` создаёт схемы лениво:

```python
# src/bioetl/domain/schemas/registry.py:41-55
def get_schema(self, name: str) -> schema_type:
    schema = self._schemas[name]
    if schema is not None:
        return schema

    # Lazy generation if schema is None
    column_order = self._schema_columns.get(name)
    generated_schema = generate_schema_from_column_order(column_order)
    self._schemas[name] = generated_schema
    return generated_schema
```

**Оставить как есть** — это обеспечивает fallback для тестов и старого кода.

---

### Задача 2.3: Добавить golden-тесты на схемы

**Цель:** Гарантировать соответствие схем ожидаемой структуре колонок.

```python
# tests/infrastructure/validation/test_schema_contracts.py
"""Golden tests for Pandera schema column structure."""

import pytest
from bioetl.domain.schemas.chembl.output_views import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.activity import (
    ActivityOutputSchema,
)
from bioetl.infrastructure.validation.schemas.chembl.assay import AssayOutputSchema


class TestSchemaColumnContracts:
    """Verify Pandera schemas match domain column specifications."""

    @pytest.mark.parametrize(
        "schema_class,expected_columns",
        [
            (ActivityOutputSchema, ACTIVITY_OUTPUT_COLUMNS),
            (AssayOutputSchema, ASSAY_OUTPUT_COLUMNS),
            # ... other schemas
        ],
    )
    def test_schema_columns_match_domain_spec(
        self, schema_class, expected_columns: list[str]
    ) -> None:
        """Verify schema columns match domain column order."""
        pandera_schema = schema_class.to_schema()
        actual_columns = list(pandera_schema.columns.keys())

        assert actual_columns == expected_columns, (
            f"Schema {schema_class.__name__} columns mismatch:\n"
            f"Expected: {expected_columns}\n"
            f"Actual: {actual_columns}"
        )
```

**Критерии готовности Фазы 2:**
- [ ] `register_pandera_schemas()` создан в infrastructure
- [ ] Composition root вызывает bootstrap схем
- [ ] Golden-тесты на соответствие колонок проходят
- [ ] Архитектурные тесты не показывают импорт domain → infrastructure
- [ ] Валидационные тесты проходят с реальными схемами

---

## Фаза 3: Избавление от глобального реестра провайдеров

**Цель:** Сделать конфигурацию провайдеров явной и тестируемой через DI.

### Задача 3.1: Анализ текущего глобального состояния

**Текущее состояние:**

```python
# src/bioetl/domain/provider_registry.py:70-95
_PROVIDER_REGISTRY: ProviderRegistryABC | None = None

def set_provider_registry(registry: ProviderRegistryABC) -> None:
    global _PROVIDER_REGISTRY
    _PROVIDER_REGISTRY = registry

def get_provider_registry() -> ProviderRegistryABC:
    if _PROVIDER_REGISTRY is None:
        raise RuntimeError("Provider registry has not been initialized...")
    return _PROVIDER_REGISTRY
```

**Проблемы:**
1. Глобальное состояние создаёт неявные зависимости
2. Порядок инициализации критичен (`set_` должен быть вызван до `get_`)
3. Параллельные тесты могут конфликтовать
4. Затруднена изоляция в unit-тестах

**Использование глобального реестра:**
```bash
grep -rn "get_provider_registry\|set_provider_registry" src/
```

---

### Задача 3.2: Внедрение реестра через DI-контейнер

**Целевая архитектура:**

```
interfaces/composition_root.py
    └── создаёт InMemoryProviderRegistry
        └── передаёт в PipelineContainer
            └── передаёт в use cases / services

# Нет глобальных переменных!
```

**Шаги выполнения:**

#### Этап 3.2.1: Добавить реестр в CompositionRoot

```python
# src/bioetl/interfaces/composition_root.py

class CompositionRoot:
    def __init__(self, ...):
        ...
        self._provider_registry: ProviderRegistryABC | None = None

    def get_provider_registry(self) -> ProviderRegistryABC:
        """Get or create provider registry instance."""
        if self._provider_registry is None:
            from bioetl.infrastructure.provider_registry import (
                InMemoryProviderRegistry,
            )
            self._provider_registry = InMemoryProviderRegistry()
            self._bootstrap_providers(self._provider_registry)
        return self._provider_registry

    def _bootstrap_providers(self, registry: ProviderRegistryABC) -> None:
        """Register default providers."""
        from bioetl.infrastructure.config.provider_registry import (
            ProviderRegistryLoader,
        )
        loader = ProviderRegistryLoader()
        loader.get_providers(registry=registry)
```

#### Этап 3.2.2: Обновить PipelineContainer для приёма реестра

```python
# src/bioetl/application/container.py

class PipelineContainer:
    def __init__(
        self,
        provider_registry: ProviderRegistryABC,  # Явная инъекция!
        schema_provider: SchemaProviderABC,
        ...
    ):
        self._provider_registry = provider_registry
        ...

    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        return self._provider_registry.get_provider(provider_id)
```

#### Этап 3.2.3: Удалить глобальные функции (deprecation period)

**Вариант A: Немедленное удаление**
```python
# src/bioetl/domain/provider_registry.py
# Удалить:
# - _PROVIDER_REGISTRY
# - set_provider_registry()
# - get_provider_registry()
# - default_provider_registry()
```

**Вариант B: Deprecation window**
```python
# src/bioetl/domain/provider_registry.py

import warnings

def get_provider_registry() -> ProviderRegistryABC:
    """DEPRECATED: Use CompositionRoot.get_provider_registry() instead."""
    warnings.warn(
        "get_provider_registry() is deprecated. "
        "Inject ProviderRegistryABC through CompositionRoot or DI container.",
        DeprecationWarning,
        stacklevel=2,
    )
    if _PROVIDER_REGISTRY is None:
        raise RuntimeError(...)
    return _PROVIDER_REGISTRY
```

#### Этап 3.2.4: Обновить тесты для изоляции реестра

```python
# tests/conftest.py

@pytest.fixture
def isolated_provider_registry() -> ProviderRegistryABC:
    """Create isolated provider registry for tests."""
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry()


@pytest.fixture
def pipeline_container(
    isolated_provider_registry: ProviderRegistryABC,
    schema_registry: SchemaProviderABC,
) -> PipelineContainer:
    """Create container with isolated dependencies."""
    return PipelineContainer(
        provider_registry=isolated_provider_registry,
        schema_provider=schema_registry,
        ...
    )
```

**Критерии готовности Фазы 3:**
- [ ] `CompositionRoot.get_provider_registry()` создан
- [ ] `PipelineContainer` принимает реестр через конструктор
- [ ] Глобальные функции помечены deprecated или удалены
- [ ] Тесты используют изолированные фикстуры
- [ ] Параллельные тесты (`pytest -n auto`) проходят без конфликтов
- [ ] Нет глобальных переменных модульного уровня

---

## Фаза 4: Усиление наблюдаемости и контроля качества

**Цель:** Обеспечить воспроизводимость и наблюдаемость пайплайнов.

### Задача 4.1: Стандартизация логирования по слоям

**Текущее состояние:**
- `LoggingPortABC` определён в `domain/observability/`
- Реализации в `infrastructure/logging/`
- Разные модули используют разные паттерны логирования

**Целевое состояние:**

```python
# Стандартный контекст для всех логов пайплайна
@dataclass
class PipelineLogContext:
    run_id: str
    provider: str
    entity: str
    stage: str  # extract | transform | load | validate

# Использование:
logger.info(
    "Processing batch",
    extra={"context": asdict(log_context), "batch_size": 100}
)
```

**Шаги выполнения:**

1. Создать `src/bioetl/domain/observability/log_context.py`:
   ```python
   @dataclass(frozen=True)
   class PipelineLogContext:
       """Structured context for pipeline logs."""
       run_id: str
       provider: str
       entity: str
       stage: str

       def as_dict(self) -> dict[str, str]:
           return asdict(self)
   ```

2. Обновить `PipelineBase` для автоматического контекста:
   ```python
   def _create_log_context(self, stage: str) -> PipelineLogContext:
       return PipelineLogContext(
           run_id=self._context.run_id,
           provider=self._context.provider,
           entity=self._context.entity_name,
           stage=stage,
       )
   ```

3. Добавить структурированное логирование в каждую стадию пайплайна

---

### Задача 4.2: Добавление метрик по стадиям

**Текущее состояние:**
- `MetricsPortABC` определён в domain
- Частичное покрытие метриками

**Целевые метрики:**

| Метрика | Тип | Описание |
|---------|-----|----------|
| `pipeline_stage_duration_seconds` | Histogram | Время выполнения стадии |
| `pipeline_records_processed_total` | Counter | Количество обработанных записей |
| `pipeline_validation_errors_total` | Counter | Количество ошибок валидации |
| `pipeline_runs_total` | Counter | Количество запусков (success/failure) |

**Шаги выполнения:**

1. Определить метрики в `domain/observability/metrics_contracts.py`
2. Реализовать в `infrastructure/observability/prometheus_metrics.py`
3. Интегрировать в `PipelineBase` через `MetricsPortABC`

---

### Задача 4.3: Документация по мониторингу

**Создать:** `docs/operations/monitoring.md`

Содержание:
- Конфигурация логирования (уровни, форматы)
- Список метрик и их значение
- Примеры Grafana dashboards
- Алерты и пороговые значения

---

## Метрики и тесты

### Новые метрики для отслеживания

| Метрика | Текущее | Целевое |
|---------|---------|---------|
| Импорты infrastructure в domain | 1 (dynamic via importlib) | 0 |
| Схемы с `None` вместо Pandera | ~7 | 0 |
| Глобальные переменные состояния | 2 (`_PROVIDER_REGISTRY`, `_default_registry`) | 0 |
| Устаревшие прокси в домене | 2 | 0 |
| Покрытие Pandera-схемами | ~60% | 100% |

### Расширение архитектурных тестов

```python
# tests/architecture/test_schema_coverage.py

def test_all_entities_have_pandera_schemas() -> None:
    """Verify all registered entity outputs have Pandera schemas."""
    from bioetl.domain.schemas.registry import get_default_schema_registry

    registry = get_default_schema_registry()
    for schema_name in registry.list_schemas():
        if schema_name.endswith("_output"):
            schema = registry.get_schema(schema_name)
            assert schema is not None, f"Schema {schema_name} is None"
            assert hasattr(schema, "to_schema"), f"Schema {schema_name} is not Pandera"


def test_no_global_mutable_state_in_domain() -> None:
    """Verify domain has no module-level mutable global state."""
    # Scan domain modules for module-level assignments
    # that are not constants (UPPER_CASE) or type aliases
    ...
```

### Связка с интегральным баллом

| Шаг | Категории, которые улучшатся | Ожидаемый рост оценки |
|-----|------------------------------|----------------------|
| Фаза 1 | Слоистая архитектура, Технический долг | +0.5 |
| Фаза 2 | Валидация данных, Ports & Adapters | +0.8 |
| Фаза 3 | Конфигурация и DI, Модульность | +0.4 |
| Фаза 4 | Наблюдаемость, Документация | +0.3 |
| **Итого** | | **+2.0** → **8.15** |

---

## Порядок выполнения

```
Фаза 1: Устранение доменных прокси (Критично)
├── 1.1 Удаление ConfigMigrator прокси         [1 час]
├── 1.2 Проверка InMemoryProviderRegistry      [30 мин]
├── 1.3 Консолидация дубликатов (если есть)    [1 час]
└── 1.4 Проверка архитектурных тестов          [30 мин]

Фаза 2: Регистрация схем и валидация (Критично)
├── 2.1 Анализ текущей регистрации             [30 мин]
├── 2.2 Создание infrastructure bootstrap       [2 часа]
├── 2.3 Golden-тесты на схемы                  [1 час]
└── 2.4 Интеграция в composition root          [1 час]

Фаза 3: Избавление от глобального реестра (Высокий)
├── 3.1 Анализ использования                   [30 мин]
├── 3.2 DI через CompositionRoot               [2 часа]
├── 3.3 Обновление PipelineContainer           [1 час]
├── 3.4 Deprecation глобальных функций         [30 мин]
└── 3.5 Обновление тестовых фикстур            [1 час]

Фаза 4: Наблюдаемость (Средний)
├── 4.1 Стандартизация логирования             [2 часа]
├── 4.2 Добавление метрик по стадиям           [2 часа]
└── 4.3 Документация по мониторингу            [1 час]
```

---

## Команды для проверки

```bash
# Архитектурные тесты (все)
pytest tests/architecture/ -v

# Проверка границ домена
pytest tests/architecture/test_domain_boundaries.py -v

# Проверка динамических импортов
pytest tests/architecture/test_domain_boundaries.py::TestDomainForbiddenImports::test_domain_has_no_dynamic_infrastructure_imports -v

# Проверка схем
pytest tests/infrastructure/validation/test_schema_contracts.py -v

# Полный набор архитектурных проверок
pytest tests/architecture/ tests/project_rules/ -v --tb=short

# Поиск импортов infrastructure в domain
grep -r "from bioetl.infrastructure\|import bioetl.infrastructure" src/bioetl/domain/

# Поиск глобальных переменных
grep -rn "^_[A-Z].*: .* = None$" src/bioetl/domain/
```

---

## Ссылки

- [Domain Layer Audit](./18-domain-layer-audit.md)
- [Architecture Tests](../../tests/architecture/)
- [Infrastructure Validation Schemas](../../src/bioetl/infrastructure/validation/schemas/)
- [Domain Schema Registry](../../src/bioetl/domain/schemas/registry.py)
