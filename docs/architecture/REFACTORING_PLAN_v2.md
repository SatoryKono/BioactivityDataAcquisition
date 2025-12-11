# План рефакторинга архитектуры v2

**Дата обновления:** 2025-12-11
**Интегральный балл архитектуры (до):** 6.38/10
**Ожидаемый интегральный балл (после):** 7.6/10
**Статус:** В работе

---

## Аудит текущего состояния

### Статус выполнения предыдущего плана (REFACTORING_PLAN.md)

| Задача | Статус | Примечание |
|--------|--------|------------|
| 1.1 Удаление ConfigMigrator прокси | ❌ НЕ ВЫПОЛНЕНО | Файл `domain/configs/migration.py` всё ещё содержит importlib прокси |
| 1.2 Консолидация InMemoryProviderRegistry | ✅ ВЫПОЛНЕНО | `memory_registry.py` удалён |
| 1.3 Тест на динамические импорты | ⚠️ ЧАСТИЧНО | Тест требует создания |
| 3.1 DefaultRunMetadataBuilder | ✅ ВЫПОЛНЕНО | Создан в `application/metadata/builder.py` |

### Выявленные архитектурные нарушения

#### 1. Application → Infrastructure (критично)

**Файл:** `src/bioetl/application/orchestrator.py:43`
```python
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
```

**Проблема:** Application слой напрямую импортирует конкретную реализацию из Infrastructure, нарушая правило "application не знает об infrastructure".

**Влияние:**
- Снижает тестируемость orchestrator (нужны моки infrastructure)
- Нарушает инверсию зависимостей (DIP)
- Затрудняет замену реализации провайдер-реестра

---

#### 2. Infrastructure → Application (прокси-модуль)

**Файл:** `src/bioetl/infrastructure/files/csv_record_source.py`
```python
raise ImportError(
    "bioetl.infrastructure.files.csv_record_source has been removed. "
    "Use bioetl.application.files.csv_record_source instead."
)
```

**Проблема:** Infrastructure содержит прокси-модуль, ссылающийся на Application, что создаёт концептуальную обратную зависимость.

**Влияние:**
- Нарушает границы слоёв на уровне документации/миграции
- Путает разработчиков относительно правильного расположения кода

---

#### 3. Infrastructure abc_impls.yaml → Application

**Файл:** `src/bioetl/infrastructure/clients/base/abc_impls.yaml`
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

**Проблема:** Конфигурация в Infrastructure содержит маппинги на Application-имплементации, что через `ABCRegistryResolverImpl` создаёт runtime-зависимость infrastructure→application.

**Влияние:**
- Нарушает принцип "infrastructure не знает об application"
- Размывает ответственность слоёв
- Усложняет понимание зависимостей

---

#### 4. Domain → Infrastructure (динамический импорт)

**Файл:** `src/bioetl/domain/configs/migration.py:32-35`
```python
mod = importlib.import_module(
    ".".join(["bioetl", "infrastructure", "config", "migration"])
)
```

**Проблема:** Domain использует importlib для обхода статических проверок импортов.

**Влияние:**
- Обходит .importlinter и статический анализ
- Нарушает чистоту доменного слоя

---

## План рефакторинга по приоритетам

### Фаза 1: Декуплинг Orchestrator (Критично)

#### Задача 1.1: Внедрение ProviderRegistry через DI

**Цель:** Убрать прямую зависимость orchestrator от конкретной реализации InMemoryProviderRegistry.

**Текущее состояние:**
```python
# src/bioetl/application/orchestrator.py:43
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

# Используется в:
# :300 - registry = loader.get_registry(registry=InMemoryProviderRegistry())
# :323 - registry = InMemoryProviderRegistry()
# :328 - return loader.get_registry(registry=InMemoryProviderRegistry())
# :330 - return InMemoryProviderRegistry()
```

**Предлагаемое решение:**

1. Добавить фабричную функцию в Domain или передавать через DI:
```python
# src/bioetl/domain/provider_registry.py (уже существует ProviderRegistryABC)
# Добавить:
ProviderRegistryFactory = Callable[[], ProviderRegistryABC]
```

2. Изменить orchestrator для приёма фабрики через конструктор:
```python
# src/bioetl/application/orchestrator.py
class PipelineOrchestrator:
    def __init__(
        self,
        pipeline_name: str,
        config: PipelineConfig,
        *,
        provider_registry: ProviderRegistryABC | None = None,
        provider_registry_factory: Callable[[], ProviderRegistryABC] | None = None,  # НОВОЕ
        # ...
    ) -> None:
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

**Критерии готовности:**
- [ ] `orchestrator.py` не содержит импортов из `bioetl.infrastructure`
- [ ] Архитектурные тесты проходят без ignore_imports для orchestrator
- [ ] Существующие тесты orchestrator проходят
- [ ] `grep "from bioetl.infrastructure" src/bioetl/application/orchestrator.py` возвращает пустой результат

**Затронутые файлы:**
- `src/bioetl/application/orchestrator.py`
- `src/bioetl/interfaces/composition_root.py`
- `tests/bioetl/application/test_orchestrator.py` (если существует)

---

### Фаза 2: Очистка Infrastructure API

#### Задача 2.1: Удаление прокси csv_record_source

**Цель:** Удалить прокси-модуль, нарушающий границы слоёв.

**Файл:** `src/bioetl/infrastructure/files/csv_record_source.py`

**Шаги:**
1. Удалить файл `src/bioetl/infrastructure/files/csv_record_source.py`
2. Обновить `.importlinter` — убрать ignore для этого пути
3. Обновить документацию миграции (если есть ссылки)

**Критерии готовности:**
- [ ] Файл `infrastructure/files/csv_record_source.py` удалён
- [ ] Нет ссылок на этот файл в codebase
- [ ] `grep -r "infrastructure.files.csv_record_source" src/` возвращает пустой результат

---

#### Задача 2.2: Удаление ConfigMigrator прокси из Domain

**Цель:** Удалить динамический импорт infrastructure в domain.

**Файл:** `src/bioetl/domain/configs/migration.py`

**Текущее состояние:**
```python
mod = importlib.import_module(
    ".".join(["bioetl", "infrastructure", "config", "migration"])
)
```

**Шаги:**
1. Обновить все импорты в тестах:
   ```python
   # Было:
   from bioetl.domain.configs.migration import ConfigMigrator
   # Стало:
   from bioetl.infrastructure.config.migration import ConfigMigrator
   ```
2. Удалить файл `src/bioetl/domain/configs/migration.py`
3. Обновить `src/bioetl/domain/configs/__init__.py` — убрать реэкспорт

**Критерии готовности:**
- [ ] Файл `domain/configs/migration.py` удалён
- [ ] Нет импортов `bioetl.domain.configs.migration` в codebase
- [ ] Архитектурные тесты проходят

---

### Фаза 3: Реорганизация ABC-реестров

#### Задача 3.1: Разделение abc_impls.yaml по слоям

**Цель:** Разорвать зависимость infrastructure→application в конфигурации реестров.

**Проблема:**
`abc_impls.yaml` в infrastructure содержит маппинги на application-классы, что создаёт концептуальную и runtime зависимость.

**Предлагаемое решение:**

**Вариант A: Переместить application-реестр в interfaces**
```
src/bioetl/
├── infrastructure/clients/base/
│   ├── abc_impls.yaml          # Только infrastructure реализации
│   └── abc_registry.yaml       # Только ABC контракты
└── interfaces/
    └── abc_impls_application.yaml  # Application реализации
```

**Вариант B: Создать фабричный реестр в application**
```python
# src/bioetl/application/factories/registry.py
APPLICATION_IMPLEMENTATIONS = {
    "PipelineContainerABC": {
        "default_factory": "bioetl.application.container.create_default_container_factory",
        "implementations": {
            "Default": "bioetl.application.container.PipelineContainer",
        },
    },
    # ...
}
```

**Шаги (Вариант A — рекомендуемый):**

1. Создать `src/bioetl/interfaces/abc_impls_application.yaml`:
```yaml
# Application layer implementations
# These are loaded by CompositionRoot, not by infrastructure

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

3. Обновить `ABCRegistryResolverImpl` для поддержки нескольких источников или создать отдельный resolver в interfaces

4. Добавить CI-линтер для проверки:
```bash
# scripts/check_abc_impls.sh
grep -q "bioetl\.application" src/bioetl/infrastructure/clients/base/abc_impls.yaml && exit 1
echo "OK: No application references in infrastructure abc_impls.yaml"
```

**Критерии готовности:**
- [ ] `grep "bioetl\.application" src/bioetl/infrastructure/clients/base/abc_impls.yaml` возвращает пустой результат
- [ ] Application-маппинги перенесены в interfaces или application
- [ ] Архитектурные тесты проходят
- [ ] Существующая функциональность сохранена

---

### Фаза 4: Расширение тестового покрытия

#### Задача 4.1: Тест на динамические импорты в Domain

**Файл:** `tests/architecture/test_domain_boundaries.py` (создать)

```python
"""Tests for domain layer boundary enforcement."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOMAIN_ROOT = Path("src/bioetl/domain")


def test_domain_has_no_dynamic_infrastructure_imports() -> None:
    """Verify domain doesn't use importlib to import infrastructure."""
    violations: list[str] = []

    for file_path in DOMAIN_ROOT.rglob("*.py"):
        code = file_path.read_text(encoding="utf-8")
        if "importlib.import_module" in code:
            if "infrastructure" in code or "application" in code:
                violations.append(
                    f"{file_path.relative_to('src')}: "
                    "dynamic import of infrastructure/application"
                )

    if violations:
        pytest.fail(
            "Domain must not dynamically import other layers:\n"
            + "\n".join(violations)
        )
```

**Критерии готовности:**
- [ ] Тест создан и проходит (после выполнения задачи 2.2)
- [ ] CI включает новый тест

---

#### Задача 4.2: Тест на abc_impls.yaml

**Файл:** `tests/architecture/test_abc_registry.py` (добавить тест)

```python
def test_infrastructure_abc_impls_has_no_application_references() -> None:
    """Verify infrastructure abc_impls.yaml doesn't reference application."""
    import yaml

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

**Критерии готовности:**
- [ ] Тест создан и проходит (после выполнения задачи 3.1)

---

#### Задача 4.3: Тесты orchestrator с моками

**Цель:** Покрыть orchestrator тестами без реальных infrastructure-зависимостей.

**Файл:** `tests/bioetl/application/test_orchestrator_unit.py`

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

**Критерии готовности:**
- [ ] Unit-тесты orchestrator без infrastructure-импортов
- [ ] Покрытие методов `_get_provider_registry`, `_load_registry_via_loader`
- [ ] Тесты проходят без warnings

---

### Фаза 5: Документация

#### Задача 5.1: Обновление .importlinter

После выполнения фаз 1-3 обновить `.importlinter`:

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

**Критерии готовности:**
- [ ] Все ignore_imports для application→infrastructure удалены
- [ ] lint-imports проходит без ошибок

---

#### Задача 5.2: Обновление ARCHITECTURE.md

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

**Критерии готовности:**
- [ ] ARCHITECTURE.md обновлён
- [ ] Добавлены примеры правильных/неправильных импортов

---

## Порядок выполнения

```
Фаза 1: Декуплинг Orchestrator (Критично)
└── 1.1 Внедрение ProviderRegistry через DI

Фаза 2: Очистка Infrastructure API (Критично)
├── 2.1 Удаление csv_record_source прокси
└── 2.2 Удаление ConfigMigrator прокси

Фаза 3: Реорганизация ABC-реестров (Высокий)
└── 3.1 Разделение abc_impls.yaml по слоям

Фаза 4: Тестовое покрытие (Средний)
├── 4.1 Тест на динамические импорты
├── 4.2 Тест на abc_impls.yaml
└── 4.3 Unit-тесты orchestrator

Фаза 5: Документация (Средний)
├── 5.1 Обновление .importlinter
└── 5.2 Обновление ARCHITECTURE.md
```

---

## Метрики успеха

| Метрика | До | После (ожидание) |
|---------|-----|------------------|
| Импорты infrastructure в application | 1 (orchestrator.py) | 0 |
| Прокси-модули infra→app | 1 (csv_record_source) | 0 |
| Динамические импорты в domain | 1 (migration.py) | 0 |
| Application-ссылки в infra YAML | 6 (abc_impls.yaml) | 0 |
| ignore_imports в .importlinter | 15+ | <5 |
| Архитектурные тесты | Pass | Pass |
| Слоистая архитектура (оценка) | 6 | 8 |
| Модульные границы (оценка) | 5 | 8 |
| Тестирование (оценка) | 6 | 7 |
| **Интегральный балл** | **6.38** | **~7.6** |

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

# Архитектурные тесты
pytest tests/architecture/ tests/project_rules/ -v

# Import linter
lint-imports
```

---

## Ссылки

- [Предыдущий план](./REFACTORING_PLAN.md)
- [Domain Layer Audit](./18-domain-layer-audit.md)
- [Architecture Tests](../../tests/architecture/)
- [.importlinter](../../.importlinter)
