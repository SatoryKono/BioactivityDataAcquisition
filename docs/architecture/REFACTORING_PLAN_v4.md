# План рефакторинга архитектуры BioETL v4



**Дата создания:** 2025-12-11

**Базовый документ:** [REFACTORING_PLAN_v3.md](./REFACTORING_PLAN_v3.md) (считается выполненным)

**Интегральный балл архитектуры (после v3):** ~8.0/10

**Целевой балл:** 8.5+

**Статус:** Планирование



---



## Оглавление



1. [Краткое резюме](#краткое-резюме)

2. [Предпосылки: что выполнено в v3](#предпосылки-что-выполнено-в-v3)

3. [Архитектурная оценка после v3](#архитектурная-оценка-после-v3)

4. [Оставшиеся проблемы](#оставшиеся-проблемы)

5. [Критические задачи](#критические-задачи)

   - [Задача 1: Ликвидация глобального состояния ProviderRegistry](#задача-1-ликвидация-глобального-состояния-providerregistry)

   - [Задача 2: Вынос Pandera-зависимости из Domain](#задача-2-вынос-pandera-зависимости-из-domain)

6. [Важные задачи](#важные-задачи)

   - [Задача 3: Консолидация глобальных синглтонов в Interfaces](#задача-3-консолидация-глобальных-синглтонов-в-interfaces)

   - [Задача 4: Сокращение ignore_imports в .importlinter](#задача-4-сокращение-ignore_imports-в-importlinter)

7. [Желательные улучшения](#желательные-улучшения)

   - [Задача 5: Очистка глобального состояния в Infrastructure](#задача-5-очистка-глобального-состояния-в-infrastructure)

   - [Задача 6: Унификация синглтонов через контекстный менеджер](#задача-6-унификация-синглтонов-через-контекстный-менеджер)

8. [Метрики и тесты для контроля](#метрики-и-тесты-для-контроля)

9. [План выполнения](#план-выполнения)

10. [Ожидаемые результаты](#ожидаемые-результаты)



---



## Краткое резюме



После выполнения плана v3 архитектура проекта достигла **целевого уровня 8.0/10**. Основные проблемы с глобальным состоянием `SchemaContractProvider` и прямым доступом к `get_pipeline_contract` в PipelineBase решены.



**Оставшиеся области для улучшения:**



1. **Глобальное состояние `_PROVIDER_REGISTRY`** в domain-слое (уже deprecated, но не удалено)

2. **Динамический импорт Pandera/YAML** в `domain/schemas/generator.py`

3. **Множественные синглтоны** в interfaces (`_default_root`, `_context`, `_factory`)

4. **Избыточные ignore_imports** в `.importlinter` (13 исключений)

5. **Глобальное состояние** в infrastructure (`_default_registry`, `_metrics_server_started`)



```

┌─────────────────────────────────────────────────────────────┐

│                      v4 Roadmap                             │

├─────────────────────────────────────────────────────────────┤

│  [v3 DONE] SchemaContractProvider DI                        │

│  [v3 DONE] PipelineBase schema injection                    │

│  [v3 DONE] CompositionRoot legacy cleanup                   │

├─────────────────────────────────────────────────────────────┤

│  [v4 TODO] ProviderRegistry DI completion                   │

│  [v4 TODO] Domain Pandera isolation                         │

│  [v4 TODO] Interfaces singleton consolidation               │

│  [v4 TODO] .importlinter ignore_imports reduction           │

└─────────────────────────────────────────────────────────────┘

```



---



## Предпосылки: что выполнено в v3



| Задача v3 | Статус | Результат |

|-----------|--------|-----------|

| 1. Ликвидация глобального состояния SchemaContractProvider | ✅ | `_SCHEMA_CONTRACT_PROVIDER` удалён из loader.py |

| 2. Инъекция схемных контрактов в PipelineBase | ✅ | `get_pipeline_contract` удалён, контракт инъектируется |

| 3. Выравнивание CompositionRoot | ✅ | Legacy параметры `logger`/`metrics` удалены |

| 4. Укрепление документации архитектуры | ✅ | Добавлены карты зависимостей и DI-примеры |

| 5. Расширение тестового набора | ✅ | Архитектурные тесты на глобальное состояние |



---



## Архитектурная оценка после v3



| Категория | До v3 | После v3 | Цель v4 |

|-----------|:-----:|:--------:|:-------:|

| Слоистая архитектура | 8 | 8.5 | 9 |

| Модульность и связность | 7 | 8 | 8.5 |

| Доменная модель | 7 | 7.5 | 8 |

| Конфигурация и DI | 6 | 8 | 8.5 |

| Обработка ошибок | 7 | 7 | 7.5 |

| Логирование и наблюдаемость | 6 | 6.5 | 7 |

| Валидация данных | 8 | 8 | 8.5 |

| Тестирование | 6 | 7.5 | 8 |

| Документация | 8 | 8.5 | 8.5 |

| Технический долг | 6 | 7.5 | 8 |

| **Интегральный балл** | **7.16** | **~8.0** | **8.5+** |



---



## Оставшиеся проблемы



### 1. Глобальное состояние в Domain



**Файл:** `src/bioetl/domain/provider_registry.py`



```python

# Строка 78

_PROVIDER_REGISTRY: ProviderRegistryABC | None = None



# Deprecated функции (строки 81-151)

def set_provider_registry(registry): ...   # DEPRECATED

def get_provider_registry(): ...           # DEPRECATED

def default_provider_registry(): ...       # DEPRECATED

```



**Использование в codebase:**

```bash

$ grep -rn "_PROVIDER_REGISTRY\|set_provider_registry\|get_provider_registry" src/

# Ожидается: 0 использований вне provider_registry.py

```



---



### 2. Динамический импорт инфраструктуры в Domain



**Файл:** `src/bioetl/domain/schemas/generator.py`



```python

# Строка 10

import importlib



# Строка 40

pa = importlib.import_module("pandera.pandas")



# Строка 63

yaml = importlib.import_module("yaml")

```



**Проблема:** Domain-слой не должен зависеть от Pandera/YAML даже через динамический импорт.



---



### 3. Множественные синглтоны в Interfaces



| Файл | Переменная | Функции |

|------|------------|---------|

| `composition_root.py` | `_default_root` | `get_composition_root()`, `reset_composition_root()` |

| `application_context.py` | `_context` | `get_application_context()`, `set_application_context()`, `reset_application_context()` |

| `use_case_factory.py` | `_factory` | `get_use_case_factory()`, `reset_use_case_factory()` |



---



### 4. Ignore_imports в .importlinter



Текущие исключения (13 штук):



```ini

ignore_imports =

    bioetl.application.config.runtime -> bioetl.infrastructure.config.loader

    bioetl.application.container -> bioetl.infrastructure.config.provider_registry

    bioetl.application.container -> bioetl.infrastructure.logging.factories

    bioetl.application.container -> bioetl.infrastructure.output.factories

    bioetl.application.container -> bioetl.infrastructure.output.unified_writer

    bioetl.application.orchestrator -> bioetl.infrastructure.provider_registry

    bioetl.application.pipelines.contracts -> bioetl.infrastructure.output.unified_writer

    bioetl.application.pipelines.hooks_impl -> bioetl.infrastructure.observability.metrics

    bioetl.application.pipelines.base -> bioetl.infrastructure.output.metadata

    bioetl.application.pipelines.base -> bioetl.infrastructure.output.unified_writer

    bioetl.application.pipelines.chembl.base -> bioetl.infrastructure.output.unified_writer

    bioetl.application.pipelines.chembl.pipeline -> bioetl.infrastructure.output.unified_writer

    bioetl.application.services.chembl_extraction -> bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl

```



---



## Критические задачи



### Задача 1: Ликвидация глобального состояния ProviderRegistry



**Приоритет:** Критично

**Влияние:** Конфигурация и DI (8→8.5), Технический долг (7.5→8)



#### Проблема



Domain-слой содержит deprecated глобальное состояние, которое не было полностью удалено:



```python

# src/bioetl/domain/provider_registry.py:78

# Global registry instance - DEPRECATED

_PROVIDER_REGISTRY: ProviderRegistryABC | None = None

```



#### Текущее использование



```bash

# Проверка прямых обращений

grep -rn "set_provider_registry\|get_provider_registry\|_PROVIDER_REGISTRY" src/ --include="*.py"

```



**Ожидаемые места использования:**

- `src/bioetl/domain/provider_registry.py` — определение

- `src/bioetl/interfaces/` — возможно legacy вызовы



#### План действий



**Этап 1.1: Аудит использования (0.5 часа)**



```bash

# Найти все использования deprecated функций

grep -rn "set_provider_registry\|get_provider_registry\|default_provider_registry" src/ tests/

```



**Этап 1.2: Миграция оставшихся вызовов (1 час)**



Заменить все вызовы на явную инъекцию через CompositionRoot:



```python

# Было:

from bioetl.domain.provider_registry import get_provider_registry

registry = get_provider_registry()



# Стало:

# Получить через DI в конструкторе или от CompositionRoot

def __init__(self, provider_registry: ProviderRegistryABC):

    self._registry = provider_registry

```



**Этап 1.3: Удаление deprecated API (0.5 часа)**



Изменить `src/bioetl/domain/provider_registry.py`:



```python

# УДАЛИТЬ:

# - _PROVIDER_REGISTRY (строка 78)

# - set_provider_registry() (строки 81-102)

# - get_provider_registry() (строки 105-129)

# - default_provider_registry() (строки 133-151)



# Обновить __all__:

__all__ = [

    # Domain abstractions

    "ProviderRegistryABC",

    "ProviderRegistryLoaderABC",

    # Domain errors

    "ProviderRegistryError",

    "ProviderNotRegisteredError",

    "ProviderAlreadyRegisteredError",

    # Type aliases for DI

    "ProviderRegistryFactory",

    # УДАЛИТЬ:

    # "get_provider_registry",

    # "set_provider_registry",

    # "default_provider_registry",

]

```



**Этап 1.4: Добавление архитектурного теста (0.5 часа)**



Расширить `tests/project_rules/test_no_global_state.py`:



```python

def test_no_global_provider_registry_in_domain(bioetl_root: Path) -> None:

    """Verify domain has no global provider registry state."""

    provider_registry_path = bioetl_root / "domain" / "provider_registry.py"



    content = provider_registry_path.read_text()



    # Check for global state pattern

    assert "_PROVIDER_REGISTRY" not in content, (

        "domain/provider_registry.py should not contain global state"

    )



    # Check for deprecated functions

    assert "def set_provider_registry" not in content

    assert "def get_provider_registry" not in content

```



#### Критерии готовности



- [ ] Глобальная переменная `_PROVIDER_REGISTRY` удалена из domain

- [ ] Функции `set_provider_registry`, `get_provider_registry`, `default_provider_registry` удалены

- [ ] Все вызовы заменены на явную инъекцию

- [ ] Архитектурный тест проходит

- [ ] Существующие тесты проходят



---



### Задача 2: Вынос Pandera-зависимости из Domain



**Приоритет:** Критично

**Влияние:** Доменная модель (7.5→8), Слоистая архитектура (8.5→9)



#### Проблема



Файл `src/bioetl/domain/schemas/generator.py` использует динамический импорт Pandera и YAML:



```python

# Строка 40

pa = importlib.import_module("pandera.pandas")



# Строка 63

yaml = importlib.import_module("yaml")

```



Это нарушает принцип чистоты domain-слоя — домен не должен знать о конкретных технологиях валидации.



#### План действий



**Этап 2.1: Создание протокола генератора схем в Domain (0.5 часа)**



Создать `src/bioetl/domain/schemas/contracts.py`:



```python

"""Domain contracts for schema generation."""

from __future__ import annotations



from abc import ABC, abstractmethod

from typing import Any, Protocol





class SchemaGeneratorProtocol(Protocol):

    """Protocol for schema generators."""



    def generate_from_column_order(self, columns: list[str]) -> Any:

        """Generate schema from column order."""

        ...





class ColumnOrderLoaderProtocol(Protocol):

    """Protocol for loading column orders from files."""



    def load(self, path: str) -> list[str]:

        """Load column order from file."""

        ...

```



**Этап 2.2: Перенос реализации в Infrastructure (1 час)**



Переместить `generate_schema_from_column_order` в `src/bioetl/infrastructure/validation/schema_generator.py`:



```python

"""Pandera schema generator implementation."""

from __future__ import annotations



import pandera.pandas as pa

import yaml

from pathlib import Path



from bioetl.domain.schemas.contracts import (

    SchemaGeneratorProtocol,

    ColumnOrderLoaderProtocol,

)





class PanderaSchemaGenerator(SchemaGeneratorProtocol):

    """Generate Pandera schemas from column descriptors."""



    def generate_from_column_order(self, columns: list[str]) -> pa.DataFrameSchema:

        """Build a permissive Pandera schema using the provided column order."""

        return pa.DataFrameSchema(

            {col: pa.Column(object, nullable=True, coerce=True) for col in columns}

        )





class YamlColumnOrderLoader(ColumnOrderLoaderProtocol):

    """Load column orders from YAML files."""



    def load(self, path: str) -> list[str]:

        """Load column order from YAML file."""

        p = Path(path)

        data = yaml.safe_load(p.read_text(encoding="utf-8"))



        if isinstance(data, list):

            return [str(x) for x in data]

        if isinstance(data, dict) and "columns" in data:

            cols = data["columns"]

            if isinstance(cols, list):

                return [str(x) for x in cols]

        raise ValueError("Invalid column-order YAML format")

```



**Этап 2.3: Обновление domain/schemas/generator.py (0.5 часа)**



Превратить в прокси с предупреждением:



```python

"""DEPRECATED: Schema generator moved to infrastructure.



Use bioetl.infrastructure.validation.schema_generator instead.

"""

from __future__ import annotations



import warnings

from typing import Any





def generate_schema_from_column_order(columns: list[str]) -> Any:

    """DEPRECATED: Use PanderaSchemaGenerator from infrastructure."""

    warnings.warn(

        "generate_schema_from_column_order is deprecated. "

        "Use bioetl.infrastructure.validation.schema_generator.PanderaSchemaGenerator",

        DeprecationWarning,

        stacklevel=2,

    )

    # Lazy import to maintain backward compatibility

    from bioetl.infrastructure.validation.schema_generator import PanderaSchemaGenerator

    return PanderaSchemaGenerator().generate_from_column_order(columns)





def load_column_order_from_yaml(path: str) -> list[str]:

    """DEPRECATED: Use YamlColumnOrderLoader from infrastructure."""

    warnings.warn(

        "load_column_order_from_yaml is deprecated. "

        "Use bioetl.infrastructure.validation.schema_generator.YamlColumnOrderLoader",

        DeprecationWarning,

        stacklevel=2,

    )

    from bioetl.infrastructure.validation.schema_generator import YamlColumnOrderLoader

    return YamlColumnOrderLoader().load(path)

```



**Этап 2.4: Добавление теста на динамические импорты (0.5 часа)**



Обновить `tests/project_rules/test_domain_isolation.py`:



```python

def test_domain_has_no_importlib_infrastructure(bioetl_root: Path) -> None:

    """Verify domain doesn't dynamically import infrastructure packages."""

    domain_dir = bioetl_root / "domain"



    infrastructure_packages = {"pandera", "yaml", "structlog", "prometheus"}

    violations = []



    for py_file in domain_dir.rglob("*.py"):

        content = py_file.read_text()

        if "importlib.import_module" in content:

            for pkg in infrastructure_packages:

                if f'"{pkg}' in content or f"'{pkg}" in content:

                    violations.append(f"{py_file}: imports {pkg}")



    assert not violations, (

        f"Domain must not dynamically import infrastructure packages:\n"

        + "\n".join(violations)

    )

```



#### Критерии готовности



- [ ] Протоколы `SchemaGeneratorProtocol`, `ColumnOrderLoaderProtocol` созданы в domain

- [ ] Реализации `PanderaSchemaGenerator`, `YamlColumnOrderLoader` созданы в infrastructure

- [ ] `domain/schemas/generator.py` содержит только deprecated прокси

- [ ] Тест на отсутствие динамических импортов проходит

- [ ] Все существующие тесты проходят



---



## Важные задачи



### Задача 3: Консолидация глобальных синглтонов в Interfaces



**Приоритет:** Важно

**Влияние:** Конфигурация и DI (8→8.5), Тестирование (7.5→8)



#### Проблема



Interfaces содержит три независимых синглтона с похожим паттерном:



| Модуль | Переменная | Проблема |

|--------|------------|----------|

| `composition_root.py` | `_default_root` | Дублирует функциональность |

| `application_context.py` | `_context` | Отдельный контейнер зависимостей |

| `use_case_factory.py` | `_factory` | Зависит от `_context` |



#### План действий



**Этап 3.1: Унификация через ApplicationContext (1.5 часа)**



Объединить все синглтоны в единый `ApplicationContext`:



```python

# src/bioetl/interfaces/application_context.py



@dataclass(frozen=True)

class ApplicationContext:

    """Unified application context with all dependencies."""



    logger: LoggingPortABC

    metrics: MetricsPortABC

    config_loader: PipelineConfigLoaderProtocol

    composition_root: CompositionRoot

    use_case_factory: UseCaseFactory



    @classmethod

    def create_default(cls) -> ApplicationContext:

        """Create context with production dependencies."""

        from bioetl.interfaces.composition_root import CompositionRoot



        root = CompositionRoot()

        # ... создание всех зависимостей



        return cls(

            logger=root.get_logger(),

            metrics=root.get_metrics(),

            config_loader=root.create_schema_contract_loader(),

            composition_root=root,

            use_case_factory=UseCaseFactory(root),

        )

```



**Этап 3.2: Удаление дублирующих синглтонов (1 час)**



Обновить `composition_root.py`:



```python

# УДАЛИТЬ:

# _default_root: CompositionRoot | None = None

# def get_composition_root() -> CompositionRoot: ...



# Использовать:

# get_application_context().composition_root

```



Обновить `use_case_factory.py`:



```python

# УДАЛИТЬ глобальный _factory

# Сделать UseCaseFactory зависимым от CompositionRoot



class UseCaseFactory:

    def __init__(self, root: CompositionRoot) -> None:

        self._root = root

```



**Этап 3.3: Обновление CLI и REST (0.5 часа)**



```python

# src/bioetl/interfaces/cli/app.py

from bioetl.interfaces.application_context import get_application_context



def run_pipeline_command(...):

    ctx = get_application_context()

    use_case = ctx.use_case_factory.create_run_pipeline_use_case()

    # ...

```



#### Критерии готовности



- [ ] Единый `ApplicationContext` содержит все зависимости

- [ ] Удалены `_default_root` и отдельный `_factory`

- [ ] CLI и REST используют единый контекст

- [ ] Тесты могут подменять контекст через `set_application_context()`



---



### Задача 4: Сокращение ignore_imports в .importlinter



**Приоритет:** Важно

**Влияние:** Слоистая архитектура (8.5→9), Модульность (8→8.5)



#### Проблема



Текущие 13 исключений в `.importlinter` указывают на нарушения границ слоёв:



```ini

ignore_imports =

    # 1. Config runtime -> loader

    bioetl.application.config.runtime -> bioetl.infrastructure.config.loader



    # 2-5. Container -> infrastructure (4 зависимости)

    bioetl.application.container -> bioetl.infrastructure.config.provider_registry

    bioetl.application.container -> bioetl.infrastructure.logging.factories

    bioetl.application.container -> bioetl.infrastructure.output.factories

    bioetl.application.container -> bioetl.infrastructure.output.unified_writer



    # 6. Orchestrator -> provider_registry

    bioetl.application.orchestrator -> bioetl.infrastructure.provider_registry



    # 7-11. Pipelines -> infrastructure (5 зависимостей)

    bioetl.application.pipelines.contracts -> bioetl.infrastructure.output.unified_writer

    bioetl.application.pipelines.hooks_impl -> bioetl.infrastructure.observability.metrics

    bioetl.application.pipelines.base -> bioetl.infrastructure.output.metadata

    bioetl.application.pipelines.base -> bioetl.infrastructure.output.unified_writer

    bioetl.application.pipelines.chembl.base -> bioetl.infrastructure.output.unified_writer

    bioetl.application.pipelines.chembl.pipeline -> bioetl.infrastructure.output.unified_writer



    # 13. Services -> impl

    bioetl.application.services.chembl_extraction -> bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl

```



#### План действий



**Этап 4.1: Вынос UnifiedWriter в domain-контракт (2 часа)**



Создать абстракцию в domain:



```python

# src/bioetl/domain/output/contracts.py



class OutputWriterABC(ABC):

    """Domain contract for writing pipeline output."""



    @abstractmethod

    def write(self, data: DataFrame, metadata: dict[str, Any]) -> Path:

        """Write data with metadata."""

```



Обновить pipelines для использования абстракции:



```python

# src/bioetl/application/pipelines/base.py



def __init__(

    self,

    # ...

    output_writer: OutputWriterABC,  # Вместо UnifiedFileWriter

):

```



**Этап 4.2: Инъекция InMemoryProviderRegistry через DI (1 час)**



(Связано с Задачей 1) — orchestrator получает `ProviderRegistryFactory` через конструктор.



**Этап 4.3: Вынос metrics hook в domain-контракт (1 час)**



```python

# src/bioetl/domain/observability/contracts.py



class MetricsHookABC(ABC):

    """Domain contract for pipeline metrics hooks."""



    @abstractmethod

    def record_stage_duration(self, stage: str, duration: float): ...



    @abstractmethod

    def increment_counter(self, name: str, value: int = 1): ...

```



**Этап 4.4: Обновление .importlinter (0.5 часа)**



После рефакторинга:



```ini

[contract:application_allowed_dependencies]

ignore_imports =

    # Оставить только неизбежные зависимости:

    bioetl.application.services.chembl_extraction -> bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl

```



**Целевое количество ignore_imports:** ≤3 (с 13)



#### Критерии готовности



- [ ] Абстракция `OutputWriterABC` создана в domain

- [ ] Pipelines используют абстракцию вместо `UnifiedFileWriter`

- [ ] `MetricsHookABC` создан в domain

- [ ] ignore_imports сокращены до ≤3

- [ ] lint-imports проходит



---



## Желательные улучшения



### Задача 5: Очистка глобального состояния в Infrastructure



**Приоритет:** Желательно

**Влияние:** Тестирование (7.5→8)



#### Проблема



Infrastructure содержит глобальные переменные:



```python

# infrastructure/chembl/model_registry.py:105

_default_registry: ChemblEntityModelRegistry | None = None



# infrastructure/observability/server.py:9

_metrics_server_started = False

```



#### План действий



1. **model_registry.py:** Заменить глобальную переменную на lazy-инициализацию в классе

2. **server.py:** Использовать контекстный менеджер для управления состоянием сервера



```python

# Было:

_metrics_server_started = False



def start_metrics_server():

    global _metrics_server_started

    if _metrics_server_started:

        return

    # ...



# Стало:

class MetricsServerManager:

    def __init__(self):

        self._started = False



    def start(self):

        if self._started:

            return

        # ...



    def stop(self):

        self._started = False

```



---



### Задача 6: Унификация синглтонов через контекстный менеджер



**Приоритет:** Желательно

**Влияние:** Тестирование (7.5→8), Модульность (8→8.5)



#### Цель



Обеспечить thread-safe и testable управление контекстом:



```python

# src/bioetl/interfaces/context_manager.py



import contextvars

from contextlib import contextmanager



_current_context: contextvars.ContextVar[ApplicationContext | None] = (

    contextvars.ContextVar("app_context", default=None)

)





def get_current_context() -> ApplicationContext:

    """Get current application context."""

    ctx = _current_context.get()

    if ctx is None:

        raise RuntimeError("No application context set")

    return ctx





@contextmanager

def application_context(ctx: ApplicationContext):

    """Context manager for application context scope."""

    token = _current_context.set(ctx)

    try:

        yield ctx

    finally:

        _current_context.reset(token)





# Использование в тестах:

def test_with_custom_context():

    custom_ctx = ApplicationContext(...)

    with application_context(custom_ctx):

        # Тест использует custom_ctx

        result = some_function()

```



---



## Метрики и тесты для контроля



### Метрики качества



| Метрика | После v3 | Целевое v4 | Способ проверки |

|---------|:--------:|:----------:|-----------------|

| Ссылки на `_PROVIDER_REGISTRY` | >0 | 0 | `grep -rn "_PROVIDER_REGISTRY" src/bioetl/domain/` |

| Динамические импорты в domain | 2 | 0 | `grep -rn "importlib.import_module" src/bioetl/domain/` |

| Синглтоны в interfaces | 3 | 1 | Аудит `_context`, `_factory`, `_default_root` |

| ignore_imports в .importlinter | 13 | ≤3 | Подсчёт строк в секции |

| Глобальные переменные в infrastructure | 2 | 0 | `grep -rn "^_[a-z].*= " src/bioetl/infrastructure/` |

| Архитектурные тесты | pass | pass | `pytest tests/project_rules/ -v` |



### Команды проверки



```bash

# Проверка глобального состояния в domain

grep -rn "_PROVIDER_REGISTRY\|_default_registry" src/bioetl/domain/



# Проверка динамических импортов в domain

grep -rn "importlib.import_module" src/bioetl/domain/



# Подсчёт ignore_imports

grep -c "bioetl\." .importlinter | grep "ignore_imports"



# Архитектурные тесты

pytest tests/project_rules/test_domain_isolation.py tests/project_rules/test_layer_architecture.py -v



# Import linter

lint-imports



# Поиск глобальных переменных

grep -rn "^_[a-z_]*:.*= None$" src/bioetl/

```



---



## План выполнения



```

КРИТИЧЕСКИЕ ЗАДАЧИ (первый приоритет)

──────────────────────────────────────



Задача 1: Ликвидация глобального состояния ProviderRegistry

├── 1.1 Аудит использования                     [0.5 ч]

├── 1.2 Миграция оставшихся вызовов             [1 ч]

├── 1.3 Удаление deprecated API                 [0.5 ч]

└── 1.4 Добавление архитектурного теста         [0.5 ч]

                                                ─────────

                                                Итого: 2.5 ч



Задача 2: Вынос Pandera-зависимости из Domain

├── 2.1 Создание протоколов в domain            [0.5 ч]

├── 2.2 Перенос реализации в infrastructure     [1 ч]

├── 2.3 Обновление domain/schemas/generator.py  [0.5 ч]

└── 2.4 Добавление теста на импорты             [0.5 ч]

                                                ─────────

                                                Итого: 2.5 ч



ВАЖНЫЕ ЗАДАЧИ (второй приоритет)

─────────────────────────────────



Задача 3: Консолидация синглтонов в Interfaces

├── 3.1 Унификация через ApplicationContext     [1.5 ч]

├── 3.2 Удаление дублирующих синглтонов         [1 ч]

└── 3.3 Обновление CLI и REST                   [0.5 ч]

                                                ─────────

                                                Итого: 3 ч



Задача 4: Сокращение ignore_imports

├── 4.1 Вынос UnifiedWriter в domain-контракт   [2 ч]

├── 4.2 Инъекция ProviderRegistry через DI      [1 ч]

├── 4.3 Вынос metrics hook в domain-контракт    [1 ч]

└── 4.4 Обновление .importlinter                [0.5 ч]

                                                ─────────

                                                Итого: 4.5 ч



ЖЕЛАТЕЛЬНЫЕ УЛУЧШЕНИЯ (третий приоритет)

────────────────────────────────────────



Задача 5: Очистка глобального состояния в Infrastructure  [2 ч]

Задача 6: Унификация через контекстный менеджер           [2 ч]

                                                          ─────────

                                                          Итого: 4 ч



═══════════════════════════════════════════════════════════════

ОБЩЕЕ ВРЕМЯ: ~16.5 ч

═══════════════════════════════════════════════════════════════

```



---



## Ожидаемые результаты



### Улучшение архитектурных оценок



| Категория | После v3 | После v4 | Изменение |

|-----------|:--------:|:--------:|:---------:|

| Слоистая архитектура | 8.5 | 9 | +0.5 |

| Модульность и связность | 8 | 8.5 | +0.5 |

| Доменная модель | 7.5 | 8 | +0.5 |

| Конфигурация и DI | 8 | 8.5 | +0.5 |

| Тестирование | 7.5 | 8 | +0.5 |



### Прогноз интегрального балла



После реализации критических задач (1, 2):

- **Доменная модель:** 7.5 → 8 (+0.05 взвешенного балла)

- **Слоистая архитектура:** 8.5 → 9 (+0.06 взвешенного балла)



**Ожидаемый интегральный балл:** 8.0 + 0.11 ≈ **8.1**



После реализации всех задач:

- **Конфигурация и DI:** 8 → 8.5 (+0.05)

- **Модульность:** 8 → 8.5 (+0.05)

- **Тестирование:** 7.5 → 8 (+0.05)



**Итоговый прогноз:** ~**8.3-8.5**



---



## Ссылки



- [Предыдущий план рефакторинга v3](./REFACTORING_PLAN_v3.md)

- [План рефакторинга v2](./REFACTORING_PLAN_v2.md)

- [Архитектурные тесты](../../tests/project_rules/)

- [Domain Provider Registry](../../src/bioetl/domain/provider_registry.py)

- [Domain Schemas Generator](../../src/bioetl/domain/schemas/generator.py)

- [Application Context](../../src/bioetl/interfaces/application_context.py)

- [.importlinter](../../.importlinter)
