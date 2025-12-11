# Объединённый план рефакторинга архитектуры BioETL

**Дата создания:** 2025-12-11
**Основан на:** REFACTORING_PLAN.md (v1) + REFACTORING_PLAN_v2.md (v2)
**Интегральный балл архитектуры (до):** 6.15-6.38/10
**Целевой балл (после):** 8.0+
**Статус:** Планирование

---

## Оглавление

1. [Сводка выявленных проблем](#сводка-выявленных-проблем)
2. [Фаза 1: Устранение нарушений границ слоёв (Критично)](#фаза-1-устранение-нарушений-границ-слоёв-критично)
3. [Фаза 2: Декуплинг Application от Infrastructure (Критично)](#фаза-2-декуплинг-application-от-infrastructure-критично)
4. [Фаза 3: Реорганизация ABC-реестров (Высокий)](#фаза-3-реорганизация-abc-реестров-высокий)
5. [Фаза 4: Избавление от глобального состояния (Высокий)](#фаза-4-избавление-от-глобального-состояния-высокий)
6. [Фаза 5: Полноценная регистрация схем и валидации (Средний)](#фаза-5-полноценная-регистрация-схем-и-валидации-средний)
7. [Фаза 6: Расширение тестового покрытия (Средний)](#фаза-6-расширение-тестового-покрытия-средний)
8. [Фаза 7: Усиление наблюдаемости (Низкий)](#фаза-7-усиление-наблюдаемости-низкий)
9. [Фаза 8: Документация и линтеры (Низкий)](#фаза-8-документация-и-линтеры-низкий)
10. [Метрики успеха](#метрики-успеха)
11. [Порядок выполнения](#порядок-выполнения)

---

## Сводка выявленных проблем

### Архитектура слоёв (напоминание)

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

Правила зависимостей:
- domain → ничего внешнего
- application → domain только
- infrastructure → domain только
- interfaces → все слои (composition root)
```

### Консолидированный список нарушений

| # | Проблема | Источник | Слой | Приоритет |
|---|----------|----------|------|-----------|
| 1 | Domain → Infrastructure (dynamic import ConfigMigrator) | v1 + v2 | Domain | Критично |
| 2 | Application → Infrastructure (orchestrator.py импортирует InMemoryProviderRegistry) | v2 | Application | Критично |
| 3 | Infrastructure → Application (csv_record_source.py прокси) | v2 | Infrastructure | Критично |
| 4 | Infrastructure abc_impls.yaml → Application (маппинги) | v2 | Infrastructure | Высокий |
| 5 | Глобальное состояние `_PROVIDER_REGISTRY` | v1 | Domain | Высокий |
| 6 | Схемы регистрируются с `schema=None` | v1 | Domain/Infra | Средний |
| 7 | Неунифицированное логирование и метрики | v1 | Все слои | Низкий |

### Статус выполнения предыдущих задач

| Задача | Статус | Примечание |
|--------|--------|------------|
| Удаление ConfigMigrator прокси | ❌ НЕ ВЫПОЛНЕНО | Файл `domain/configs/migration.py` всё ещё содержит importlib прокси |
| Консолидация InMemoryProviderRegistry | ✅ ВЫПОЛНЕНО | `memory_registry.py` удалён |
| DefaultRunMetadataBuilder | ✅ ВЫПОЛНЕНО | Создан в `application/metadata/builder.py` |
| Тест на динамические импорты | ⚠️ ЧАСТИЧНО | Тест существует, но не проходит из-за migration.py |

---

## Фаза 1: Устранение нарушений границ слоёв (Критично)

**Цель:** Восстановить строгую направленность зависимостей domain → ничего внешнего.

### Задача 1.1: Удаление ConfigMigrator прокси из Domain

**Источник:** v1 (задача 1.1) + v2 (задача 2.2)

**Проблема:**
Файл `src/bioetl/domain/configs/migration.py` содержит динамический импорт из infrastructure:

```python
# src/bioetl/domain/configs/migration.py:32-35
mod = importlib.import_module(
    ".".join(["bioetl", "infrastructure", "config", "migration"])
)
return getattr(mod, "ConfigMigrator")
```

**Влияние:**
- Обходит `.importlinter` и статический анализ
- Нарушает чистоту доменного слоя
- Deprecation warning уже работает → безопасно удалять

**Шаги выполнения:**

1. Проверить внешние зависимости:
   ```bash
   grep -r "from bioetl.domain.configs.migration import\|from bioetl.domain.configs import ConfigMigrator" src/ tests/
   ```

2. Обновить импорты (если найдены):
   ```python
   # Было:
   from bioetl.domain.configs.migration import ConfigMigrator
   # Стало:
   from bioetl.infrastructure.config.migration import ConfigMigrator
   ```

3. Удалить файл:
   ```bash
   rm src/bioetl/domain/configs/migration.py
   ```

4. Обновить `src/bioetl/domain/configs/__init__.py` — удалить строки 141-153:
   ```python
   # Удалить блок:
   # if name == "ConfigMigrator":
   #     ...
   #     return ConfigMigrator
   ```

5. Запустить архитектурные тесты:
   ```bash
   pytest tests/architecture/test_domain_boundaries.py -v
   ```

**Критерии готовности:**
- [ ] Файл `domain/configs/migration.py` удалён
- [ ] Нет `__getattr__` для ConfigMigrator в `domain/configs/__init__.py`
- [ ] `grep -r "from bioetl.domain.configs.migration" src/ tests/` возвращает пустой результат
- [ ] Архитектурный тест `test_domain_has_no_dynamic_infrastructure_imports` проходит

**Затронутые файлы:**
- `src/bioetl/domain/configs/migration.py` (удалить)
- `src/bioetl/domain/configs/__init__.py` (обновить)
- `tests/` (обновить импорты, если есть)

---

### Задача 1.2: Удаление csv_record_source прокси из Infrastructure

**Источник:** v2 (задача 2.1)

**Проблема:**
Infrastructure содержит прокси-модуль, ссылающийся на Application:

```python
# src/bioetl/infrastructure/files/csv_record_source.py
raise ImportError(
    "bioetl.infrastructure.files.csv_record_source has been removed. "
    "Use bioetl.application.files.csv_record_source instead."
)
```

**Влияние:**
- Нарушает границы слоёв на уровне документации/миграции
- Путает разработчиков относительно правильного расположения кода

**Шаги выполнения:**

1. Проверить внешние зависимости:
   ```bash
   grep -r "infrastructure.files.csv_record_source" src/ tests/
   ```

2. Удалить файл:
   ```bash
   rm src/bioetl/infrastructure/files/csv_record_source.py
   ```

3. Обновить `.importlinter` — убрать ignore для этого пути (если есть)

**Критерии готовности:**
- [ ] Файл `infrastructure/files/csv_record_source.py` удалён
- [ ] `grep -r "infrastructure.files.csv_record_source" src/` возвращает пустой результат

**Затронутые файлы:**
- `src/bioetl/infrastructure/files/csv_record_source.py` (удалить)

---

### Задача 1.3: Проверка InMemoryProviderRegistry прокси

**Источник:** v1 (задача 1.2)

**Текущее состояние:**
```python
# src/bioetl/domain/provider_registry.py:104-111
def __getattr__(name: str) -> Any:
    if name == "InMemoryProviderRegistry":
        raise ImportError(
            "InMemoryProviderRegistry is no longer available in bioetl.domain. "
            "Import it from bioetl.infrastructure.provider_registry instead."
        )
    raise AttributeError(...)
```

**Действие:** Оставить как есть — это корректно предотвращает импорт и помогает миграции.

**Проверка:**
```bash
grep -r "from bioetl.domain.provider_registry import InMemoryProviderRegistry" src/ tests/
grep -r "from bioetl.domain import.*InMemoryProviderRegistry" src/ tests/
```

**Критерий готовности:**
- [ ] Нет реальных импортов `InMemoryProviderRegistry` из domain

---

## Фаза 2: Декуплинг Application от Infrastructure (Критично)

**Цель:** Убрать прямые зависимости application слоя от конкретных реализаций infrastructure.

### Задача 2.1: Внедрение ProviderRegistry через DI в Orchestrator

**Источник:** v2 (задача 1.1)

**Проблема:**
```python
# src/bioetl/application/orchestrator.py:43
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

# Используется в:
# :300 - registry = loader.get_registry(registry=InMemoryProviderRegistry())
# :323 - registry = InMemoryProviderRegistry()
# :328 - return loader.get_registry(registry=InMemoryProviderRegistry())
# :330 - return InMemoryProviderRegistry()
```

**Влияние:**
- Снижает тестируемость orchestrator (нужны моки infrastructure)
- Нарушает инверсию зависимостей (DIP)
- Затрудняет замену реализации провайдер-реестра

**Предлагаемое решение:**

1. Добавить фабричный тип в Domain:
   ```python
   # src/bioetl/domain/provider_registry.py
   from typing import Callable

   ProviderRegistryFactory = Callable[[], ProviderRegistryABC]
   ```

2. Изменить orchestrator для приёма фабрики через конструктор:
   ```python
   # src/bioetl/application/orchestrator.py
   from bioetl.domain.provider_registry import ProviderRegistryABC, ProviderRegistryFactory

   class PipelineOrchestrator:
       def __init__(
           self,
           pipeline_name: str,
           config: PipelineConfig,
           *,
           provider_registry: ProviderRegistryABC | None = None,
           provider_registry_factory: ProviderRegistryFactory | None = None,  # НОВОЕ
           # ...
       ) -> None:
           self._provider_registry = provider_registry
           self._provider_registry_factory = provider_registry_factory

       def _get_provider_registry(self) -> ProviderRegistryABC:
           if self._provider_registry is not None:
               return self._provider_registry
           if self._provider_registry_factory is not None:
               return self._provider_registry_factory()
           raise RuntimeError("No provider registry or factory provided")
   ```

3. Перенести создание InMemoryProviderRegistry в interfaces/composition_root:
   ```python
   # src/bioetl/interfaces/composition_root.py
   from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

   def create_orchestrator(...) -> PipelineOrchestrator:
       return PipelineOrchestrator(
           ...,
           provider_registry_factory=InMemoryProviderRegistry,
       )
   ```

4. Удалить импорт из orchestrator:
   ```python
   # Удалить:
   # from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
   ```

**Критерии готовности:**
- [ ] `orchestrator.py` не содержит импортов из `bioetl.infrastructure`
- [ ] `grep "from bioetl.infrastructure" src/bioetl/application/orchestrator.py` возвращает пустой результат
- [ ] Архитектурные тесты проходят без ignore_imports для orchestrator
- [ ] Существующие тесты orchestrator проходят

**Затронутые файлы:**
- `src/bioetl/domain/provider_registry.py` (добавить ProviderRegistryFactory)
- `src/bioetl/application/orchestrator.py` (рефакторинг)
- `src/bioetl/interfaces/composition_root.py` (обновить создание)
- `tests/bioetl/application/test_orchestrator.py` (если существует)

---

## Фаза 3: Реорганизация ABC-реестров (Высокий)

**Цель:** Разорвать зависимость infrastructure → application в конфигурации реестров.

### Задача 3.1: Разделение abc_impls.yaml по слоям

**Источник:** v2 (задача 3.1)

**Проблема:**
Файл `src/bioetl/infrastructure/clients/base/abc_impls.yaml` содержит маппинги на application-классы:

```yaml
PipelineContainerABC:
  default_factory: bioetl.application.container.create_default_container_factory
  implementations:
    Default: bioetl.application.container.PipelineContainer

PipelineHookABC:
  default_factory: bioetl.application.factories.hooks.PipelineHookFactory
  implementations:
    Logging: bioetl.application.pipelines.hooks_impl.LoggingPipelineHookImpl
    Metrics: bioetl.application.pipelines.hooks_impl.MetricsPipelineHookImpl

ErrorPolicyABC:
  default_factory: bioetl.application.pipelines.hooks_impl.FailFastErrorPolicyImpl
  implementations:
    FailFast: bioetl.application.pipelines.hooks_impl.FailFastErrorPolicyImpl
    ContinueOnError: bioetl.application.pipelines.hooks_impl.ContinueOnErrorPolicyImpl
```

**Влияние:**
- Нарушает принцип "infrastructure не знает об application"
- Создаёт runtime-зависимость через `ABCRegistryResolverImpl`
- Усложняет понимание архитектуры

**Предлагаемое решение (Вариант A — рекомендуемый):**

Разделить YAML-файлы по слоям:

```
src/bioetl/
├── infrastructure/clients/base/
│   ├── abc_impls.yaml          # Только infrastructure реализации
│   └── abc_registry.yaml       # Только ABC контракты
└── interfaces/
    └── abc_impls_application.yaml  # Application реализации
```

**Шаги выполнения:**

1. Создать `src/bioetl/interfaces/abc_impls_application.yaml`:
   ```yaml
   # Application layer implementations
   # Loaded by CompositionRoot, not by infrastructure

   PipelineContainerABC:
     default_factory: bioetl.application.container.create_default_container_factory
     implementations:
       Default: bioetl.application.container.PipelineContainer

   PipelineHookABC:
     default_factory: bioetl.application.factories.hooks.PipelineHookFactory
     implementations:
       Logging: bioetl.application.pipelines.hooks_impl.LoggingPipelineHookImpl
       Metrics: bioetl.application.pipelines.hooks_impl.MetricsPipelineHookImpl

   ErrorPolicyABC:
     default_factory: bioetl.application.pipelines.hooks_impl.FailFastErrorPolicyImpl
     implementations:
       FailFast: bioetl.application.pipelines.hooks_impl.FailFastErrorPolicyImpl
       ContinueOnError: bioetl.application.pipelines.hooks_impl.ContinueOnErrorPolicyImpl
   ```

2. Удалить application-маппинги из `infrastructure/clients/base/abc_impls.yaml`

3. Обновить `ABCRegistryResolverImpl` или composition root для загрузки нескольких YAML-файлов

4. Добавить CI-проверку:
   ```bash
   # scripts/check_abc_impls.sh
   grep -q "bioetl\.application" src/bioetl/infrastructure/clients/base/abc_impls.yaml && exit 1
   echo "OK: No application references in infrastructure abc_impls.yaml"
   ```

**Критерии готовности:**
- [ ] `grep "bioetl\.application" src/bioetl/infrastructure/clients/base/abc_impls.yaml` возвращает пустой результат
- [ ] Application-маппинги перенесены в `interfaces/abc_impls_application.yaml`
- [ ] Архитектурные тесты проходят
- [ ] Существующая функциональность сохранена

**Затронутые файлы:**
- `src/bioetl/infrastructure/clients/base/abc_impls.yaml` (очистить от application)
- `src/bioetl/interfaces/abc_impls_application.yaml` (создать)
- `src/bioetl/interfaces/composition_root.py` (обновить загрузку)
- `ABCRegistryResolverImpl` (возможно обновить)

---

## Фаза 4: Избавление от глобального состояния (Высокий)

**Цель:** Сделать конфигурацию провайдеров явной и тестируемой через DI.

### Задача 4.1: Анализ текущего глобального состояния

**Источник:** v1 (задачи 3.1-3.2)

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
2. Порядок инициализации критичен
3. Параллельные тесты могут конфликтовать
4. Затруднена изоляция в unit-тестах

### Задача 4.2: Внедрение реестра через DI-контейнер

**Шаги выполнения:**

1. Добавить реестр в CompositionRoot:
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

2. Обновить PipelineContainer для приёма реестра:
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
   ```

3. Пометить глобальные функции deprecated:
   ```python
   # src/bioetl/domain/provider_registry.py

   import warnings

   def get_provider_registry() -> ProviderRegistryABC:
       """DEPRECATED: Use CompositionRoot.get_provider_registry() instead."""
       warnings.warn(
           "get_provider_registry() is deprecated. "
           "Inject ProviderRegistryABC through CompositionRoot.",
           DeprecationWarning,
           stacklevel=2,
       )
       if _PROVIDER_REGISTRY is None:
           raise RuntimeError(...)
       return _PROVIDER_REGISTRY
   ```

4. Обновить тесты для изоляции:
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

**Критерии готовности:**
- [ ] `CompositionRoot.get_provider_registry()` создан
- [ ] `PipelineContainer` принимает реестр через конструктор
- [ ] Глобальные функции помечены deprecated
- [ ] Тесты используют изолированные фикстуры
- [ ] Параллельные тесты (`pytest -n auto`) проходят без конфликтов

**Затронутые файлы:**
- `src/bioetl/interfaces/composition_root.py`
- `src/bioetl/application/container.py`
- `src/bioetl/domain/provider_registry.py`
- `tests/conftest.py`

---

## Фаза 5: Полноценная регистрация схем и валидации (Средний)

**Цель:** Гарантировать валидацию на уровне инфраструктуры, оставить домен чистым от Pandera.

### Задача 5.1: Создать инфраструктурный bootstrap для схем

**Источник:** v1 (задачи 2.1-2.3)

**Проблема:**
Домен регистрирует схемы с `schema=None`:
```python
# src/bioetl/domain/schemas/__init__.py:37-38
for name, cols in mapping.items():
    provider.register(name, None, column_order=cols)  # schema=None!
```

**Решение:**

1. Создать `src/bioetl/infrastructure/validation/registry_bootstrap.py`:
   ```python
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
           try:
               column_order = registry.get_schema_columns(name)
           except ValueError:
               column_order = None

           registry.register(name, schema_class, column_order=column_order)

       return registry
   ```

2. Обновить composition root:
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

### Задача 5.2: Golden-тесты на схемы

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

**Критерии готовности:**
- [ ] `register_pandera_schemas()` создан в infrastructure
- [ ] Composition root вызывает bootstrap схем
- [ ] Golden-тесты на соответствие колонок проходят
- [ ] Валидационные тесты проходят с реальными схемами

**Затронутые файлы:**
- `src/bioetl/infrastructure/validation/registry_bootstrap.py` (создать)
- `src/bioetl/interfaces/composition_root.py` (обновить)
- `tests/infrastructure/validation/test_schema_contracts.py` (создать)

---

## Фаза 6: Расширение тестового покрытия (Средний)

### Задача 6.1: Тест на динамические импорты в Domain

**Источник:** v1 (задача 1.4) + v2 (задача 4.1)

**Файл:** `tests/architecture/test_domain_boundaries.py`

Тест уже существует (`test_domain_has_no_dynamic_infrastructure_imports`), но не проходит из-за `domain/configs/migration.py`. После выполнения Фазы 1 тест должен проходить.

**Критерии готовности:**
- [ ] Тест `test_domain_has_no_dynamic_infrastructure_imports` проходит
- [ ] CI включает этот тест

---

### Задача 6.2: Тест на abc_impls.yaml

**Источник:** v2 (задача 4.2)

**Файл:** `tests/architecture/test_abc_registry.py` (создать/добавить)

```python
def test_infrastructure_abc_impls_has_no_application_references() -> None:
    """Verify infrastructure abc_impls.yaml doesn't reference application."""
    import yaml
    from pathlib import Path

    impls_path = Path("src/bioetl/infrastructure/clients/base/abc_impls.yaml")
    content = impls_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    violations: list[str] = []
    for role, config in data.items():
        default_factory = config.get("default_factory", "")
        if "bioetl.application" in default_factory:
            violations.append(f"{role}.default_factory -> {default_factory}")

        for impl_name, impl_path in config.get("implementations", {}).items():
            if "bioetl.application" in impl_path:
                violations.append(f"{role}.implementations.{impl_name} -> {impl_path}")

    if violations:
        pytest.fail(
            "Infrastructure abc_impls.yaml must not reference application:\n"
            + "\n".join(violations)
        )
```

---

### Задача 6.3: Unit-тесты orchestrator с моками

**Источник:** v2 (задача 4.3)

**Файл:** `tests/bioetl/application/test_orchestrator_unit.py` (создать)

```python
"""Unit tests for PipelineOrchestrator with mocked dependencies."""
from unittest.mock import MagicMock

import pytest

from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.provider_registry import ProviderRegistryABC


@pytest.fixture
def mock_registry() -> MagicMock:
    return MagicMock(spec=ProviderRegistryABC)


@pytest.fixture
def mock_config() -> PipelineConfig:
    # Minimal valid config
    return PipelineConfig(...)


def test_orchestrator_uses_injected_registry(
    mock_config: PipelineConfig,
    mock_registry: MagicMock,
) -> None:
    """Orchestrator should use injected registry without infrastructure imports."""
    orchestrator = PipelineOrchestrator(
        "test_pipeline",
        mock_config,
        provider_registry=mock_registry,
    )
    # ...
```

---

### Задача 6.4: Тест на отсутствие глобального состояния в Domain

**Источник:** v1 (раздел "Метрики и тесты")

```python
# tests/architecture/test_domain_boundaries.py

def test_no_global_mutable_state_in_domain() -> None:
    """Verify domain has no module-level mutable global state."""
    import ast
    from pathlib import Path

    domain_root = Path("src/bioetl/domain")
    violations: list[str] = []

    for py_file in domain_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                # Check for _VARIABLE: Type = None pattern
                if (
                    isinstance(node.target, ast.Name)
                    and node.target.id.startswith("_")
                    and not node.target.id.isupper()
                ):
                    violations.append(f"{py_file}: {node.target.id}")

    if violations:
        pytest.fail(
            "Domain should not have mutable global state:\n"
            + "\n".join(violations)
        )
```

**Критерии готовности Фазы 6:**
- [ ] Все архитектурные тесты проходят
- [ ] Тест на abc_impls.yaml добавлен и проходит (после Фазы 3)
- [ ] Unit-тесты orchestrator созданы
- [ ] Тест на глобальное состояние добавлен

---

## Фаза 7: Усиление наблюдаемости (Низкий)

**Источник:** v1 (Фаза 4)

### Задача 7.1: Стандартизация логирования по слоям

1. Создать `src/bioetl/domain/observability/log_context.py`:
   ```python
   from dataclasses import dataclass, asdict

   @dataclass(frozen=True)
   class PipelineLogContext:
       """Structured context for pipeline logs."""
       run_id: str
       provider: str
       entity: str
       stage: str  # extract | transform | load | validate

       def as_dict(self) -> dict[str, str]:
           return asdict(self)
   ```

2. Обновить `PipelineBase` для автоматического контекста

### Задача 7.2: Добавление метрик по стадиям

Целевые метрики:

| Метрика | Тип | Описание |
|---------|-----|----------|
| `pipeline_stage_duration_seconds` | Histogram | Время выполнения стадии |
| `pipeline_records_processed_total` | Counter | Количество обработанных записей |
| `pipeline_validation_errors_total` | Counter | Количество ошибок валидации |
| `pipeline_runs_total` | Counter | Количество запусков (success/failure) |

---

## Фаза 8: Документация и линтеры (Низкий)

### Задача 8.1: Обновление .importlinter

**Источник:** v2 (задача 5.1)

После выполнения фаз 1-4 обновить `.importlinter`:

```ini
[contract:application_allowed_dependencies]
name = Application imports domain only
type = forbidden
source_modules =
    bioetl.application
forbidden_modules =
    bioetl.infrastructure
    bioetl.interfaces
# Убрать все ignore_imports для infrastructure
```

### Задача 8.2: Обновление ARCHITECTURE.md

**Источник:** v2 (задача 5.2)

Добавить раздел о границах слоёв:

```markdown
## Layer Boundaries

### Domain Layer
- NEVER imports from infrastructure, application, or interfaces
- NEVER uses importlib to dynamically import other layers
- Contains only: contracts (ABC, Protocol), value objects, pure business logic

### Application Layer
- MAY import from domain only
- NEVER imports from infrastructure or interfaces
- Contains: use cases, orchestration, factories, mappers

### Infrastructure Layer
- MAY import from domain only
- NEVER imports from application or interfaces
- Contains: HTTP clients, file I/O, databases, external services

### Interfaces Layer
- MAY import from all layers
- Contains: CLI, REST, composition root, dependency wiring
```

### Задача 8.3: Документация по мониторингу

**Создать:** `docs/operations/monitoring.md`

---

## Метрики успеха

### Количественные метрики

| Метрика | До | После (ожидание) |
|---------|-----|------------------|
| Импорты infrastructure в application | 1 (orchestrator.py) | 0 |
| Прокси-модули infra→app | 1 (csv_record_source) | 0 |
| Динамические импорты в domain | 1 (migration.py) | 0 |
| Application-ссылки в infra YAML | 6 (abc_impls.yaml) | 0 |
| ignore_imports в .importlinter | 15+ | <5 |
| Схемы с `None` вместо Pandera | ~7 | 0 |
| Глобальные переменные состояния | 2 | 0 (deprecated) |

### Оценка по категориям

| Категория | До | После |
|-----------|-----|-------|
| Слоистая архитектура | 6-7 | 8 |
| Ports & Adapters / DDD | 6 | 7 |
| Модульность и связность | 5-6 | 8 |
| Конфигурация и DI | 5.5 | 7.5 |
| Валидация данных и схемы | 5 | 7 |
| Тестирование и QA-гейты | 6-7 | 8 |
| Логирование и наблюдаемость | 6 | 7 |
| **Интегральный балл** | **6.15-6.38** | **~8.0** |

---

## Порядок выполнения

```
Фаза 1: Устранение нарушений границ слоёв (Критично)
├── 1.1 Удаление ConfigMigrator прокси из domain
├── 1.2 Удаление csv_record_source прокси из infrastructure
└── 1.3 Проверка InMemoryProviderRegistry прокси

Фаза 2: Декуплинг Application от Infrastructure (Критично)
└── 2.1 Внедрение ProviderRegistry через DI в Orchestrator

Фаза 3: Реорганизация ABC-реестров (Высокий)
└── 3.1 Разделение abc_impls.yaml по слоям

Фаза 4: Избавление от глобального состояния (Высокий)
├── 4.1 Анализ текущего глобального состояния
└── 4.2 Внедрение реестра через DI-контейнер

Фаза 5: Регистрация схем и валидация (Средний)
├── 5.1 Создание infrastructure bootstrap для схем
└── 5.2 Golden-тесты на схемы

Фаза 6: Расширение тестового покрытия (Средний)
├── 6.1 Тест на динамические импорты в Domain
├── 6.2 Тест на abc_impls.yaml
├── 6.3 Unit-тесты orchestrator с моками
└── 6.4 Тест на глобальное состояние

Фаза 7: Усиление наблюдаемости (Низкий)
├── 7.1 Стандартизация логирования
└── 7.2 Добавление метрик по стадиям

Фаза 8: Документация и линтеры (Низкий)
├── 8.1 Обновление .importlinter
├── 8.2 Обновление ARCHITECTURE.md
└── 8.3 Документация по мониторингу
```

---

## Команды для проверки

```bash
# Проверка импортов application→infrastructure
grep -r "from bioetl.infrastructure" src/bioetl/application/

# Проверка импортов infrastructure→application
grep -r "from bioetl.application" src/bioetl/infrastructure/

# Проверка динамических импортов в domain
grep -r "importlib.import_module" src/bioetl/domain/

# Проверка abc_impls.yaml
grep "bioetl\.application" src/bioetl/infrastructure/clients/base/abc_impls.yaml

# Проверка глобальных переменных
grep -rn "^_[A-Z].*: .* = None$" src/bioetl/domain/

# Архитектурные тесты
pytest tests/architecture/ tests/project_rules/ -v

# Import linter
lint-imports
```

---

## Ссылки

- [REFACTORING_PLAN.md](./REFACTORING_PLAN.md) — исходный план v1
- [REFACTORING_PLAN_v2.md](./REFACTORING_PLAN_v2.md) — план v2 с фокусом на границы слоёв
- [Domain Layer Audit](./18-domain-layer-audit.md)
- [Architecture Tests](../../tests/architecture/)
- [.importlinter](../../.importlinter)
