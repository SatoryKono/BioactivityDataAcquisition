# План рефакторинга архитектуры BioETL v3

**Дата создания:** 2025-12-11
**Интегральный балл архитектуры:** 7.16/10
**Целевой балл:** 8.0+
**Статус:** Планирование

---

## Оглавление

1. [Краткое резюме](#краткое-резюме)
2. [Архитектурная оценка](#архитектурная-оценка)
3. [Архитектурные наблюдения](#архитектурные-наблюдения)
4. [Критические задачи](#критические-задачи)
   - [Задача 1: Ликвидация глобального состояния SchemaContractProvider](#задача-1-ликвидация-глобального-состояния-schemacontractprovider)
   - [Задача 2: Инъекция схемных контрактов в PipelineBase](#задача-2-инъекция-схемных-контрактов-в-pipelinebase)
5. [Важные задачи](#важные-задачи)
   - [Задача 3: Выравнивание CompositionRoot](#задача-3-выравнивание-compositionroot)
6. [Желательные улучшения](#желательные-улучшения)
   - [Задача 4: Укрепление документации архитектуры](#задача-4-укрепление-документации-архитектуры)
   - [Задача 5: Расширение тестового набора](#задача-5-расширение-тестового-набора)
7. [Метрики и тесты для контроля](#метрики-и-тесты-для-контроля)
8. [План выполнения](#план-выполнения)
9. [Ожидаемые результаты](#ожидаемые-результаты)

---

## Краткое резюме

Архитектура проекта демонстрирует **устойчивую среднюю зрелость** (7.16/10), что указывает на необходимость целевых улучшений. Основные проблемные области:

- **Глобальное состояние** `_SCHEMA_CONTRACT_PROVIDER` в конфигурационном загрузчике
- **Прямой доступ** PipelineBase к глобальным функциям `get_pipeline_contract`
- **Legacy-параметры** в CompositionRoot для обратной совместимости

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

---

## Архитектурная оценка

| Категория | Описание | Вес | Оценка (1–10) | Взвешенный балл |
|-----------|----------|-----|---------------|-----------------|
| Слоистая архитектура | Соответствие разделению domain/application/infrastructure и запретам на зависимости | 0.12 | 8 | 0.96 |
| Модульность и связность | Чистота интерфейсов, отсутствие сквозных зависимостей | 0.10 | 7 | 0.70 |
| Доменная модель | Чёткость портов/контрактов и моделей | 0.10 | 7 | 0.70 |
| Конфигурация и DI | Прозрачность загрузки конфигов и отсутствие глобального состояния | 0.10 | 6 | 0.60 |
| Обработка ошибок и устойчивость | Политики ошибок, fail-fast, деградация | 0.08 | 7 | 0.56 |
| Логирование и наблюдаемость | Наличие фабрик/портов для логов и метрик | 0.08 | 6 | 0.48 |
| Валидация данных и схемы | Схемы, контракты, строгая проверка | 0.10 | 8 | 0.80 |
| Тестирование | Покрытие, архитектурные проверки | 0.10 | 6 | 0.60 |
| Документация и стайлгайды | Полнота и актуальность правил | 0.12 | 8 | 0.96 |
| Технический долг и сопровождаемость | Deprecated API, legacy слои, чистота API | 0.10 | 6 | 0.60 |
| **Итого** | | **1.0** | | **7.16** |

**Интерпретация:** 5–7.9 = «устойчивая средняя зрелость, но нужны целевые улучшения».

---

## Архитектурные наблюдения

### Сильные стороны

1. **Слоистая структура** (domain/application/infrastructure/interfaces) и запреты на пересечение зависимостей формализованы через архитектурный тестовый набор в `tests/project_rules/test_layer_architecture.py`, что поддерживает Ports & Adapters-дисциплину.

2. **Composition Root** (`src/bioetl/interfaces/composition_root.py`) концентрирует сборку зависимостей и фабрики наблюдаемости/инфраструктуры.

3. **PipelineBase** чётко реализует шаблон Extract→Transform→Validate→Write и интегрирует валидацию/метаданные через `StageRuntimeManager`.

4. **Документация и правила качества** подробно заданы, включая обязательные архитектурные проверки.

### Проблемные области

1. **Глобальное состояние провайдера схем** в `src/bioetl/infrastructure/config/loader.py`:
   ```python
   _SCHEMA_CONTRACT_PROVIDER: SchemaContractProviderABC | None = None
   ```
   Это тормозит переход на чистый DI и допускает неявные зависимости.

2. **Прямой доступ к глобальным контрактам** в PipelineBase:
   ```python
   # src/bioetl/application/pipelines/base.py:132-134
   self._schema_contract = get_pipeline_contract(
       config.id, default_entity=config.entity_name
   )
   ```

3. **Обходные пути** к бизнес-ключам в конфиге через reflection на `hashing`:
   ```python
   # src/bioetl/application/pipelines/base.py:182-200
   def _resolve_business_key_fields(self) -> list[str] | None:
       hashing_section = getattr(self._config, "hashing", None)
       if isinstance(hashing_section, property):
           hashing_section = (
               hashing_section.fget(self._config) if hashing_section.fget else None
           )
       ...
   ```

4. **Legacy-параметры** в CompositionRoot для обратной совместимости:
   ```python
   # src/bioetl/interfaces/composition_root.py:84-88
   # Legacy parameters (backward compatibility)
   logger: LoggingPortABC | None = None,
   metrics: MetricsPortABC | None = None,
   http_session_factory: type | None = None,
   ```

---

## Критические задачи

### Задача 1: Ликвидация глобального состояния SchemaContractProvider

**Приоритет:** Критично
**Влияние:** Конфигурация и DI (6→8), Технический долг (6→7.5)

#### Проблема

Файл `src/bioetl/infrastructure/config/loader.py` содержит глобальную переменную и deprecated функции:

```python
_SCHEMA_CONTRACT_PROVIDER: SchemaContractProviderABC | None = None

def set_schema_contract_provider(provider: SchemaContractProviderABC) -> None:
    """DEPRECATED"""
    global _SCHEMA_CONTRACT_PROVIDER
    _SCHEMA_CONTRACT_PROVIDER = provider

def get_schema_contract_provider() -> SchemaContractProviderABC | None:
    """DEPRECATED"""
    return _SCHEMA_CONTRACT_PROVIDER
```

#### Текущее использование

```bash
# Поиск прямых обращений к глобальному провайдеру
grep -rn "_SCHEMA_CONTRACT_PROVIDER\|set_schema_contract_provider\|get_schema_contract_provider" src/ --include="*.py"
```

**Файлы с использованием:**
- `src/bioetl/infrastructure/config/loader.py` — определение и internal функции
- `src/bioetl/application/bootstrap.py` — через `_set_provider_internal`
- `src/bioetl/interfaces/bootstrap_factory.py` — инъекция при bootstrap

#### План действий

**Этап 1.1: Аудит использования (0.5 часа)**

```bash
# Проверить все места использования
grep -rn "set_schema_contract_provider\|_set_provider_internal" src/ tests/
```

**Этап 1.2: Удаление deprecated функций из публичного API (1 час)**

Изменить `src/bioetl/infrastructure/config/loader.py`:

```python
# УДАЛИТЬ из __all__:
# - "set_schema_contract_provider"
# - "get_schema_contract_provider"
# - "clear_schema_contract_provider"
# - "reset_schema_contract_provider"
# - "create_schema_contract_loader"

# ОСТАВИТЬ только:
__all__ = [
    "SchemaContractLoader",
    "ConfigFileNotFoundError",
    "UnknownProviderError",
    "get_pipeline_config",
    "get_pipeline_config_from_path",
]
```

**Этап 1.3: Обновление bootstrap_factory (1 час)**

Изменить `src/bioetl/interfaces/bootstrap_factory.py` для использования только явной инъекции:

```python
def create_default_bootstrap() -> ApplicationBootstrap:
    """Create ApplicationBootstrap with infrastructure hooks."""
    from bioetl.infrastructure.validation.bootstrap import register_schemas

    # НЕ использовать _set_provider_internal
    # Вместо этого передавать provider через config_loader_factory

    def config_loader_factory(
        provider: SchemaContractProviderABC,
    ) -> PipelineConfigLoaderProtocol:
        from bioetl.infrastructure.config.loader import SchemaContractLoader
        return SchemaContractLoader(provider)

    return ApplicationBootstrap(
        config_loader_factory=config_loader_factory,
        schema_register_fn=register_schemas,
        # Убрать provider_injector — больше не нужен
    )
```

**Этап 1.4: Удаление internal функций (0.5 часа)**

После обновления всех использований удалить из loader.py:

```python
# УДАЛИТЬ:
def _set_provider_internal(provider: SchemaContractProviderABC) -> None:
    ...

def _clear_provider_internal() -> None:
    ...

_SCHEMA_CONTRACT_PROVIDER: SchemaContractProviderABC | None = None
```

**Этап 1.5: Добавление архитектурного теста (0.5 часа)**

Создать `tests/project_rules/test_no_global_state.py`:

```python
"""Tests for absence of global mutable state."""

import ast
from pathlib import Path
import pytest

def test_no_global_schema_provider_in_infrastructure(bioetl_root: Path) -> None:
    """Verify infrastructure has no global schema provider state."""
    loader_path = bioetl_root / "infrastructure" / "config" / "loader.py"

    content = loader_path.read_text()
    tree = ast.parse(content)

    global_assignments = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id.startswith("_")
        and "PROVIDER" in node.target.id
    ]

    assert not global_assignments, (
        f"Found global state variables: "
        f"{[n.target.id for n in global_assignments]}"
    )
```

#### Критерии готовности

- [ ] Глобальная переменная `_SCHEMA_CONTRACT_PROVIDER` удалена
- [ ] Функции `set_schema_contract_provider`, `get_schema_contract_provider` удалены
- [ ] Функции `_set_provider_internal`, `_clear_provider_internal` удалены
- [ ] Bootstrap использует только явную инъекцию через factories
- [ ] Архитектурный тест на отсутствие глобального состояния проходит
- [ ] Все существующие тесты проходят

---

### Задача 2: Инъекция схемных контрактов в PipelineBase

**Приоритет:** Критично
**Влияние:** Модульность (7→8), Тестирование (6→7)

#### Проблема

PipelineBase использует глобальную функцию `get_pipeline_contract`:

```python
# src/bioetl/application/pipelines/base.py:63
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract

# src/bioetl/application/pipelines/base.py:132-134
self._schema_contract = get_pipeline_contract(
    config.id, default_entity=config.entity_name
)
```

Это создаёт:
- Скрытую зависимость на глобальный реестр `PIPELINE_CONTRACTS`
- Затруднение подмены контрактов в тестах
- Нарушение явных границ ответственности

#### План действий

**Этап 2.1: Добавление контракта как параметра конструктора (1 час)**

Изменить `src/bioetl/application/pipelines/base.py`:

```python
from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel

class PipelineBase(ABC):
    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        loader: LoaderABC,
        hash_service: HashServiceABC,
        index_generator: IndexGeneratorABC,
        timestamp_provider: TimestampProviderABC,
        schema_contract: PipelineSchemaModel,  # НОВЫЙ ПАРАМЕТР
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        extractor: ExtractorABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        transformer: TransformerABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._config = config
        # ...
        self._schema_contract = schema_contract  # Использовать инъектированный
        # УДАЛИТЬ:
        # self._schema_contract = get_pipeline_contract(...)
```

**Этап 2.2: Обновление фабрик пайплайнов (1.5 часа)**

Обновить `src/bioetl/application/pipelines/chembl/factories.py` и другие фабрики:

```python
def create_chembl_activity_pipeline(
    container: PipelineContainerABC,
    config: PipelineConfig,
    schema_contract_provider: SchemaContractProviderABC,  # НОВЫЙ ПАРАМЕТР
) -> ChEMBLActivityPipeline:
    """Create ChEMBL activity pipeline with injected dependencies."""

    schema_contract = schema_contract_provider.get_contract(
        config.id,
        default_entity=config.entity_name,
    )

    return ChEMBLActivityPipeline(
        config=config,
        logger=container.logger,
        validation_service=container.validation_service,
        loader=container.loader,
        hash_service=container.hash_service,
        index_generator=container.index_generator,
        timestamp_provider=container.timestamp_provider,
        schema_contract=schema_contract,
        # ...
    )
```

**Этап 2.3: Обновление PipelineContainer (1 час)**

Изменить `src/bioetl/application/container.py`:

```python
class PipelineContainer(PipelineContainerABC):
    def __init__(
        self,
        config: PipelineConfig,
        *,
        logger: LoggingPortABC,
        loader: LoaderABC,
        # ...
        schema_contract_provider: SchemaContractProviderABC | None = None,
    ) -> None:
        # ...
        self._schema_contract_provider = schema_contract_provider

    @property
    def schema_contract_provider(self) -> SchemaContractProviderABC:
        """Get schema contract provider."""
        if self._schema_contract_provider is None:
            raise RuntimeError(
                "SchemaContractProvider not configured. "
                "Pass it through constructor."
            )
        return self._schema_contract_provider
```

**Этап 2.4: Обновление CompositionRoot (0.5 часа)**

Изменить `src/bioetl/interfaces/composition_root.py`:

```python
def create_pipeline_container(
    self,
    config: PipelineConfig,
    *,
    provider_registry: ProviderRegistryABC | None = None,
    provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
) -> PipelineContainerABC:
    # ...
    return PipelineContainer(
        config,
        logger=self.get_logger(),
        loader=loader,
        # ...
        schema_contract_provider=self.get_schema_contract_provider(),  # ДОБАВИТЬ
    )
```

**Этап 2.5: Удаление импорта глобальной функции (0.5 часа)**

После миграции удалить из base.py:

```python
# УДАЛИТЬ импорт:
# from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
```

#### Критерии готовности

- [ ] `PipelineBase.__init__` принимает `schema_contract` как параметр
- [ ] Все фабрики пайплайнов обновлены для передачи контракта
- [ ] `PipelineContainer` хранит `schema_contract_provider`
- [ ] `CompositionRoot` передаёт провайдер в контейнер
- [ ] Импорт `get_pipeline_contract` удалён из base.py
- [ ] Тесты используют mock-контракты для изоляции

---

## Важные задачи

### Задача 3: Выравнивание CompositionRoot

**Приоритет:** Важно
**Влияние:** Конфигурация и DI (6→7), Модульность (7→7.5)

#### Проблема

CompositionRoot содержит legacy-параметры для обратной совместимости:

```python
def __init__(
    self,
    *,
    # New factory parameters
    observability_factory: ObservabilityFactoryABC | None = None,
    infrastructure_factory: InfrastructureFactoryABC | None = None,
    # Legacy parameters (backward compatibility)
    logger: LoggingPortABC | None = None,          # ← legacy
    metrics: MetricsPortABC | None = None,         # ← legacy
    http_session_factory: type | None = None,      # ← legacy
    schema_contract_provider: SchemaContractProviderABC | None = None,
) -> None:
```

#### План действий

**Этап 3.1: Перевод logger/metrics на фабрики (1 час)**

```python
class CompositionRoot:
    def __init__(
        self,
        *,
        observability_factory: ObservabilityFactoryABC | None = None,
        infrastructure_factory: InfrastructureFactoryABC | None = None,
        # Убрать legacy параметры logger/metrics
        http_config: HttpClientConfig | None = None,  # Вместо session_factory
        schema_contract_provider: SchemaContractProviderABC | None = None,
    ) -> None:
        self._observability = observability_factory or DefaultObservabilityFactory()
        self._infrastructure = infrastructure_factory or DefaultInfrastructureFactory()

        # Убрать _explicit_logger / _explicit_metrics
        self._http_config = http_config
```

**Этап 3.2: Создание адаптеров для legacy API (1 час)**

Создать `src/bioetl/interfaces/legacy_adapters.py`:

```python
"""Legacy adapters for backward compatibility."""

import warnings
from bioetl.interfaces.composition_root import CompositionRoot

def create_composition_root_with_legacy(
    *,
    logger=None,
    metrics=None,
    **kwargs,
) -> CompositionRoot:
    """Create CompositionRoot with legacy parameter support.

    DEPRECATED: Pass observability_factory instead.
    """
    if logger is not None or metrics is not None:
        warnings.warn(
            "logger/metrics parameters are deprecated. "
            "Use observability_factory instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Create custom factory with provided instances
        # ...

    return CompositionRoot(**kwargs)
```

**Этап 3.3: Обновление документации (0.5 часа)**

Добавить примеры миграции в `docs/migration/composition-root-v2.md`.

#### Критерии готовности

- [ ] Legacy параметры `logger`/`metrics` удалены из `__init__`
- [ ] Создан адаптер `create_composition_root_with_legacy` с deprecation warnings
- [ ] Документация по миграции обновлена
- [ ] Все тесты обновлены для использования фабрик

---

## Желательные улучшения

### Задача 4: Укрепление документации архитектуры

**Приоритет:** Желательно
**Влияние:** Документация (8→8.5)

#### План действий

1. **Добавить карту зависимостей** в `docs/architecture/dependency-map.md`:
   - Диаграмма слоёв с направлением импортов
   - Список разрешённых/запрещённых зависимостей
   - Примеры правильной инъекции

2. **Примеры DI-потока** в `docs/02-pipelines/di-examples.md`:
   - Создание pipeline через CompositionRoot
   - Переопределение зависимостей для тестов
   - Использование mock-провайдеров

3. **CLI-гайд по конфигурации** в `docs/cli/configuration.md`:
   - Загрузка конфигов через SchemaContractLoader
   - Профили и переопределения
   - Примеры YAML-конфигураций

---

### Задача 5: Расширение тестового набора

**Приоритет:** Желательно
**Влияние:** Тестирование (6→7.5)

#### План действий

**Этап 5.1: Тест на отсутствие глобальных провайдеров**

```python
# tests/project_rules/test_no_global_state.py

def test_no_global_provider_references_in_application(bioetl_root: Path) -> None:
    """Verify application layer doesn't use global provider state."""
    application_dir = bioetl_root / "application"

    violations = []
    for py_file in application_dir.rglob("*.py"):
        content = py_file.read_text()
        if "_SCHEMA_CONTRACT_PROVIDER" in content:
            violations.append(str(py_file))
        if "get_pipeline_contract" in content and "import" not in content:
            # Check for direct usage, not just import
            violations.append(f"{py_file}: uses get_pipeline_contract")

    assert not violations, f"Found global state references: {violations}"
```

**Этап 5.2: Интеграционный тест конфиг-загрузчика**

```python
# tests/integration/test_config_loader_di.py

def test_config_loader_with_explicit_provider() -> None:
    """Test config loading with explicit provider injection."""
    from bioetl.interfaces.composition_root import CompositionRoot

    root = CompositionRoot()
    loader = root.create_schema_contract_loader()

    config = loader.get_pipeline_config("chembl.activity")

    assert config.id == "chembl.activity"
    assert config.entity_name == "activity"
```

**Этап 5.3: Unit-тест PipelineBase с mock-контрактом**

```python
# tests/bioetl/application/pipelines/test_pipeline_base_di.py

def test_pipeline_base_uses_injected_contract() -> None:
    """Test that PipelineBase uses injected schema contract."""
    from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel

    mock_contract = PipelineSchemaModel(
        pipeline_code="test.pipeline",
        schema_out="test_output",
        schema_in="test_input",
        output_schema="test_output",
    )

    # Create pipeline with mock contract
    pipeline = TestPipeline(
        config=mock_config,
        schema_contract=mock_contract,
        # ... other deps
    )

    assert pipeline._schema_contract == mock_contract
    assert pipeline._schema_contract.schema_out == "test_output"
```

---

## Метрики и тесты для контроля

### Метрики качества

| Метрика | Текущее | Целевое | Способ проверки |
|---------|---------|---------|-----------------|
| Ссылки на `_SCHEMA_CONTRACT_PROVIDER` | >0 | 0 | `grep -rn "_SCHEMA_CONTRACT_PROVIDER" src/` |
| Ссылки на `get_pipeline_contract` в application | >0 | 0 | `grep -rn "get_pipeline_contract" src/bioetl/application/` |
| Deprecated функций в публичном API | ~8 | 0 | Анализ `__all__` экспортов |
| Архитектурные тесты | pass | pass | `pytest tests/project_rules/ -v` |
| Покрытие unit-тестами DI | ~60% | 90% | `pytest --cov` |

### Команды проверки

```bash
# Проверка глобального состояния
grep -rn "_SCHEMA_CONTRACT_PROVIDER\|get_pipeline_contract" src/bioetl/application/ src/bioetl/infrastructure/

# Архитектурные тесты
pytest tests/project_rules/test_layer_architecture.py -v

# Полный набор архитектурных проверок
pytest tests/project_rules/ -v --tb=short

# Проверка deprecated функций
grep -rn "DeprecationWarning" src/bioetl/infrastructure/config/loader.py

# Поиск глобальных переменных
grep -rn "^_[A-Z].*: .* = None$" src/bioetl/
```

---

## План выполнения

```
КРИТИЧЕСКИЕ ЗАДАЧИ (первый приоритет)
──────────────────────────────────────

Задача 1: Ликвидация глобального состояния SchemaContractProvider
├── 1.1 Аудит использования                           [0.5 ч]
├── 1.2 Удаление deprecated функций из публичного API [1 ч]
├── 1.3 Обновление bootstrap_factory                  [1 ч]
├── 1.4 Удаление internal функций                     [0.5 ч]
└── 1.5 Добавление архитектурного теста               [0.5 ч]
                                                      ─────────
                                                      Итого: 3.5 ч

Задача 2: Инъекция схемных контрактов в PipelineBase
├── 2.1 Добавление контракта как параметра            [1 ч]
├── 2.2 Обновление фабрик пайплайнов                  [1.5 ч]
├── 2.3 Обновление PipelineContainer                  [1 ч]
├── 2.4 Обновление CompositionRoot                    [0.5 ч]
└── 2.5 Удаление импорта глобальной функции           [0.5 ч]
                                                      ─────────
                                                      Итого: 4.5 ч

ВАЖНЫЕ ЗАДАЧИ (второй приоритет)
─────────────────────────────────

Задача 3: Выравнивание CompositionRoot
├── 3.1 Перевод logger/metrics на фабрики             [1 ч]
├── 3.2 Создание адаптеров для legacy API             [1 ч]
└── 3.3 Обновление документации                       [0.5 ч]
                                                      ─────────
                                                      Итого: 2.5 ч

ЖЕЛАТЕЛЬНЫЕ УЛУЧШЕНИЯ (третий приоритет)
────────────────────────────────────────

Задача 4: Укрепление документации архитектуры        [2 ч]
Задача 5: Расширение тестового набора                [2 ч]
                                                      ─────────
                                                      Итого: 4 ч

═══════════════════════════════════════════════════════════════
ОБЩЕЕ ВРЕМЯ: ~14.5 ч
═══════════════════════════════════════════════════════════════
```

---

## Ожидаемые результаты

### Улучшение архитектурных оценок

| Категория | До | После | Изменение |
|-----------|:--:|:-----:|:---------:|
| Конфигурация и DI | 6 | 8 | +2 |
| Технический долг | 6 | 7.5 | +1.5 |
| Модульность и связность | 7 | 8 | +1 |
| Тестирование | 6 | 7.5 | +1.5 |

### Прогноз интегрального балла

После реализации критических задач (1, 2):
- **Конфигурация и DI:** 6 → 8 (+0.20 взвешенного балла)
- **Технический долг:** 6 → 7.5 (+0.15 взвешенного балла)

**Ожидаемый интегральный балл:** 7.16 + 0.35 ≈ **7.5**

После реализации всех задач:
- **Модульность:** 7 → 8 (+0.10)
- **Тестирование:** 6 → 7.5 (+0.15)

**Итоговый прогноз:** ~**8.0**

---

## Ссылки

- [Предыдущий план рефакторинга v2](./REFACTORING_PLAN_v2.md)
- [Архитектурные тесты](../../tests/project_rules/)
- [CompositionRoot](../../src/bioetl/interfaces/composition_root.py)
- [PipelineBase](../../src/bioetl/application/pipelines/base.py)
- [Config Loader](../../src/bioetl/infrastructure/config/loader.py)
- [Schema Contracts](../../src/bioetl/domain/schemas/pipeline_contracts.py)
