# Объединённый план рефакторинга архитектуры BioETL

**Версия:** 2.0 (консолидация v5 + docs/REFACTORING_PLAN)
**Дата создания:** 2025-12-11
**Базовые документы:**
- [docs/REFACTORING_PLAN.md](../REFACTORING_PLAN.md) — фокус на interfaces layer (26 импортов)
- [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md) — фокус на application layer + инкапсуляция

**Текущий интегральный балл:** 6.4–6.8/10
**Целевой интегральный балл:** ≥7.5/10
**Статус:** Планирование

---

## Оглавление

1. [Резюме](#резюме)
2. [Консолидированная оценка архитектуры](#консолидированная-оценка-архитектуры)
3. [Полный реестр выявленных проблем](#полный-реестр-выявленных-проблем)
4. [Приоритеты рефакторинга](#приоритеты-рефакторинга)
5. [Фаза 1: Изоляция application от infrastructure](#фаза-1-изоляция-application-от-infrastructure)
6. [Фаза 2: Изоляция interfaces от infrastructure](#фаза-2-изоляция-interfaces-от-infrastructure)
7. [Фаза 3: Публичный API и инкапсуляция](#фаза-3-публичный-api-и-инкапсуляция)
8. [Фаза 4: Централизация сервисов](#фаза-4-централизация-сервисов)
9. [Фаза 5: Усиление архитектурных тестов](#фаза-5-усиление-архитектурных-тестов)
10. [Фаза 6: Устранение технического долга](#фаза-6-устранение-технического-долга)
11. [Метрики и контроль](#метрики-и-контроль)
12. [План выполнения](#план-выполнения)
13. [Ожидаемые результаты](#ожидаемые-результаты)

---

## Резюме

Данный документ объединяет два плана рефакторинга с разными фокусами:

| План | Фокус | Ключевые проблемы |
|------|-------|-------------------|
| docs/REFACTORING_PLAN.md | interfaces → infrastructure | 26 прямых импортов в interfaces layer |
| REFACTORING_PLAN_v5.md | application → infrastructure | Fallback в orchestrator, приватные методы |

### Общая картина нарушений

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE VIOLATIONS MAP                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐                                                      │
│   │  INTERFACES  │──────┐                                               │
│   │   (26 imp)   │      │                                               │
│   └──────────────┘      │    DIRECT IMPORTS                             │
│          ↓              │    (should go through ports)                  │
│   ┌──────────────┐      │                                               │
│   │ APPLICATION  │──────┼───────────────────┐                           │
│   │   (1 imp)    │      │                   │                           │
│   │   (_private) │      │                   ↓                           │
│   └──────────────┘      │         ┌─────────────────┐                   │
│          ↓              └────────→│ INFRASTRUCTURE  │                   │
│   ┌──────────────┐                │    (impl)       │                   │
│   │    DOMAIN    │                └─────────────────┘                   │
│   │  (pandera?)  │                                                      │
│   │  (global st) │                                                      │
│   └──────────────┘                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Ключевые цели

1. **Устранить 27 прямых зависимостей** на инфраструктуру из верхних слоёв
2. **Создать публичные API** для внутренних операций пайплайнов
3. **Централизовать сервисы** (наблюдаемость, конфигурация)
4. **Ликвидировать глобальное состояние** и внешние зависимости в domain
5. **Закрепить архитектурные правила** автоматизированными тестами

---

## Консолидированная оценка архитектуры

| Категория | Вес | Оценка | Взвеш. балл | Проблемы |
|-----------|:---:|:------:|:-----------:|----------|
| Слоистая архитектура | 0.12 | 6.5 | 0.78 | interfaces→infra, application→infra |
| Ports & Adapters / DDD | 0.10 | 6 | 0.60 | Недостаточное использование портов |
| Границы модулей | 0.10 | 6 | 0.60 | Приватные методы, утечки абстракций |
| Качество доменной модели | 0.10 | 7 | 0.70 | Pandera в domain |
| Контракты и конфигурация | 0.08 | 6 | 0.48 | Отсутствует ConfigurationService |
| Обработка ошибок | 0.10 | 6 | 0.60 | Нет централизованного логирования |
| Тестирование и QA | 0.10 | 6 | 0.60 | Недостаточные архитектурные проверки |
| Валидация данных | 0.10 | 7 | 0.70 | — |
| Документация | 0.10 | 7 | 0.70 | — |
| Сопровождаемость | 0.10 | 6 | 0.60 | Глобальное состояние, ignore_imports |
| **Интегральный балл** | **1.00** | | **6.36** | |

---

## Полный реестр выявленных проблем

### Категория A: Нарушения слоистой архитектуры

| ID | Слой | Файл | Строка | Описание | Источник | Приоритет |
|:--:|------|------|:------:|----------|:--------:|:---------:|
| A1 | application | `orchestrator.py` | 58-69 | Импорт `InMemoryProviderRegistry` через fallback | v5 | Критический |
| A2 | interfaces | `composition_root.py` | — | 10 прямых импортов infrastructure | v1 | Критический |
| A3 | interfaces | `bootstrap_factory.py` | — | 2 прямых импорта infrastructure | v1 | Высокий |
| A4 | interfaces | `factories/infrastructure.py` | — | 4 прямых импорта infrastructure | v1 | Высокий |
| A5 | interfaces | `factories/observability.py` | — | 2 прямых импорта infrastructure | v1 | Высокий |
| A6 | interfaces | `cli/app.py` | — | 2 прямых импорта infrastructure | v1 | Средний |
| A7 | interfaces | `use_case_factory.py` | — | 2 прямых импорта infrastructure | v1 | Средний |
| A8 | interfaces | `application_context.py` | — | 1 прямой импорт infrastructure | v1 | Средний |
| A9 | interfaces | `monitoring/__init__.py` | — | 3 прямых импорта infrastructure | v1 | Средний |

### Категория B: Нарушения инкапсуляции

| ID | Файл | Строка | Описание | Источник | Приоритет |
|:--:|------|:------:|----------|:--------:|:---------:|
| B1 | `orchestrator.py` | 156 | Вызов `pipeline._get_extract_callable()` | v5 | Высокий |
| B2 | `orchestrator.py` | 157-159 | Вызов `pipeline._normalize_extract_result()` | v5 | Высокий |

### Категория C: Технический долг

| ID | Файл | Описание | Источник | Приоритет |
|:--:|------|----------|:--------:|:---------:|
| C1 | `domain/provider_registry.py` | Глобальное состояние `_PROVIDER_REGISTRY` | v5/v4 | Средний |
| C2 | `domain/schemas/generator.py` | Pandera/YAML импорты в domain | v5/v4 | Средний |
| C3 | `.importlinter` | 13 исключений (целевое: ≤3) | v5/v4 | Низкий |

### Категория D: Недостающие компоненты

| ID | Описание | Источник | Приоритет |
|:--:|----------|:--------:|:---------:|
| D1 | Порты фабрик в application слое | v1 | Критический |
| D2 | Адаптеры фабрик в infrastructure | v1 | Критический |
| D3 | ObservabilityService | v1 | Высокий |
| D4 | ConfigurationService | v1 | Средний |
| D5 | Тесты на инфраструктурные импорты | v5 | Высокий |
| D6 | Тесты на приватные атрибуты | v5 | Средний |

---

## Приоритеты рефакторинга

```
ПРИОРИТЕТ 1: КРИТИЧЕСКИЙ (Блокирующие нарушения)
══════════════════════════════════════════════════════════════════
   [A1] Fallback InMemoryProviderRegistry в orchestrator (v5)
   [A2] 10 импортов infrastructure в composition_root.py (v1)
   [D1] Создание портов в application/ports/ (v1)
   [D2] Создание адаптеров в infrastructure/adapters/ (v1)

ПРИОРИТЕТ 2: ВЫСОКИЙ (Инкапсуляция и архитектурные тесты)
══════════════════════════════════════════════════════════════════
   [B1-B2] Публичный API для extract-only режима (v5)
   [A3-A5] Прямые импорты в factories и bootstrap (v1)
   [D3] ObservabilityService (v1)
   [D5] Тесты на инфраструктурные импорты (v5)

ПРИОРИТЕТ 3: СРЕДНИЙ (Сервисы и CLI)
══════════════════════════════════════════════════════════════════
   [A6-A9] Прямые импорты в CLI, use_case_factory, monitoring (v1)
   [D4] ConfigurationService (v1)
   [D6] Тесты на приватные атрибуты (v5)

ПРИОРИТЕТ 4: НИЗКИЙ (Технический долг)
══════════════════════════════════════════════════════════════════
   [C1] Глобальное состояние ProviderRegistry (v4)
   [C2] Pandera в Domain (v4)
   [C3] Сокращение ignore_imports (v4)
```

---

## Фаза 1: Изоляция application от infrastructure

**Приоритет:** Критический
**Источник:** REFACTORING_PLAN_v5.md
**Решает:** A1
**Время:** ~3.5 часа

### Задача 1.1: Удаление fallback в PipelineOrchestrator

**Файл:** `src/bioetl/application/orchestrator.py`

**Текущий код (проблема):**
```python
def _get_default_registry_factory() -> ProviderRegistryFactory:
    """Get the default provider registry factory."""
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry

class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory | None = None,
    ) -> None:
        self._provider_registry_factory = (
            provider_registry_factory or _get_default_registry_factory()
        )
```

**Целевой код:**
```python
class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory,  # обязательный!
    ) -> None:
        self._provider_registry_factory = provider_registry_factory
```

### Задача 1.2: Фабрика в composition root

**Создать:** `src/bioetl/interfaces/factories/provider_registry.py`

```python
"""Provider registry factory for composition root."""
from __future__ import annotations

from bioetl.domain.provider_registry import ProviderRegistryFactory


def create_provider_registry_factory() -> ProviderRegistryFactory:
    """Create the default provider registry factory.

    This is the single place where infrastructure is imported for DI.
    """
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry
```

### Задача 1.3: Обновление точек входа

**Обновить:** `src/bioetl/interfaces/composition_root.py`

```python
from bioetl.interfaces.factories.provider_registry import (
    create_provider_registry_factory,
)

class CompositionRoot:
    def create_orchestrator(
        self,
        pipeline_name: str,
        config: PipelineConfig,
    ) -> PipelineOrchestrator:
        return PipelineOrchestrator(
            pipeline_name,
            config,
            provider_registry_factory=create_provider_registry_factory(),
            # ... остальные зависимости
        )
```

### Задача 1.4: Обновление тестов

```python
# В тестах:
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

orchestrator = PipelineOrchestrator(
    "test_pipeline",
    config,
    provider_registry_factory=InMemoryProviderRegistry,
)
```

### Критерии готовности Фазы 1

- [ ] В `application/orchestrator.py` нет импортов `bioetl.infrastructure.*`
- [ ] Функция `_get_default_registry_factory()` удалена
- [ ] `provider_registry_factory` — обязательный параметр конструктора
- [ ] Все тесты проходят

---

## Фаза 2: Изоляция interfaces от infrastructure

**Приоритет:** Критический
**Источник:** docs/REFACTORING_PLAN.md
**Решает:** A2–A9, D1–D2
**Время:** ~6 часов

### Задача 2.1: Создать порты в application слое

**Новые файлы:**

```
src/bioetl/application/ports/
├── __init__.py
├── config_loader_port.py          # ConfigLoaderPortABC
├── infrastructure_factory_port.py  # InfrastructureFactoryPortABC
└── observability_factory_port.py   # ObservabilityFactoryPortABC
```

**Файл:** `src/bioetl/application/ports/config_loader_port.py`

```python
"""Port for configuration loading operations."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from bioetl.domain.configs.pipeline import PipelineConfig


class ConfigLoaderPortABC(ABC):
    """Abstract port for loading pipeline configurations."""

    @abstractmethod
    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        """Load pipeline config by ID (e.g., 'chembl.activity')."""
        ...

    @abstractmethod
    def get_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        """Load pipeline config from explicit file path."""
        ...


class ConfigPathResolverPortABC(ABC):
    """Abstract port for resolving configuration paths."""

    @abstractmethod
    def get_configs_root(self) -> Path:
        """Return root directory for configurations."""
        ...

    @abstractmethod
    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        """Resolve path for a pipeline ID."""
        ...
```

**Файл:** `src/bioetl/application/ports/infrastructure_factory_port.py`

```python
"""Port for infrastructure component factories."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.clients.base.contracts import HttpClientABC, RateLimiterABC


class InfrastructureFactoryPortABC(ABC):
    """Abstract factory for infrastructure components."""

    @abstractmethod
    def create_http_client(self, base_url: str, **kwargs) -> "HttpClientABC":
        """Create HTTP client instance."""
        ...

    @abstractmethod
    def create_rate_limiter(
        self, requests_per_second: float, **kwargs
    ) -> "RateLimiterABC":
        """Create rate limiter instance."""
        ...


class ABCRegistryResolverPortABC(ABC):
    """Abstract port for resolving ABC implementations."""

    @abstractmethod
    def resolve(self, abc_name: str) -> type:
        """Resolve implementation class for given ABC name."""
        ...

    @abstractmethod
    def resolve_instance(self, abc_name: str, **kwargs) -> object:
        """Resolve and instantiate implementation for given ABC name."""
        ...
```

**Файл:** `src/bioetl/application/ports/observability_factory_port.py`

```python
"""Port for observability component factories."""
from abc import ABC, abstractmethod

from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
    TracingPortABC,
)


class ObservabilityFactoryPortABC(ABC):
    """Abstract factory for observability components."""

    @abstractmethod
    def create_logger(self) -> LoggingPortABC:
        """Create structured logger instance."""
        ...

    @abstractmethod
    def create_metrics(self) -> MetricsPortABC:
        """Create metrics collector instance."""
        ...

    @abstractmethod
    def create_tracer(self) -> TracingPortABC | None:
        """Create tracer instance (optional)."""
        ...
```

### Задача 2.2: Создать адаптеры в infrastructure слое

**Новые файлы:**

```
src/bioetl/infrastructure/adapters/
├── __init__.py
├── config_loader_adapter.py
├── infrastructure_factory_adapter.py
└── observability_factory_adapter.py
```

**Файл:** `src/bioetl/infrastructure/adapters/config_loader_adapter.py`

```python
"""Infrastructure adapter for config loading port."""
from pathlib import Path
from typing import Any

from bioetl.application.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.domain.configs.pipeline import PipelineConfig
from bioetl.infrastructure.config.loader import (
    get_pipeline_config,
    get_pipeline_config_from_path,
)
from bioetl.infrastructure.config.sources import (
    get_configs_root as infra_get_configs_root,
    resolve_pipeline_config_path,
)


class ConfigLoaderAdapter(ConfigLoaderPortABC):
    """Adapter implementing config loader port."""

    def __init__(self, schema_contract_provider):
        self._provider = schema_contract_provider

    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        return get_pipeline_config(
            pipeline_id,
            schema_contract_provider=self._provider,
            profile=profile,
            cli_overrides=cli_overrides or {},
            env_overrides=env_overrides or {},
        )

    def get_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        return get_pipeline_config_from_path(
            config_path,
            schema_contract_provider=self._provider,
            profile=profile,
            cli_overrides=cli_overrides or {},
        )


class ConfigPathResolverAdapter(ConfigPathResolverPortABC):
    """Adapter implementing config path resolver port."""

    def __init__(self, base_dir: Path | None = None):
        self._base_dir = base_dir

    def get_configs_root(self) -> Path:
        return infra_get_configs_root(self._base_dir)

    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        return resolve_pipeline_config_path(pipeline_id, self._base_dir)
```

### Задача 2.3: Рефакторинг CompositionRoot

**Файл:** `src/bioetl/interfaces/composition_root.py`

```python
# БЫЛО (26 прямых импортов infrastructure):
from bioetl.infrastructure.config.loader import SchemaContractLoader
from bioetl.infrastructure.config.sources import get_configs_root
# ... ещё импорты

# СТАНЕТ (импорты только портов из application):
from bioetl.application.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.application.ports.infrastructure_factory_port import (
    InfrastructureFactoryPortABC,
    ABCRegistryResolverPortABC,
)
from bioetl.application.ports.observability_factory_port import (
    ObservabilityFactoryPortABC,
)


class CompositionRoot:
    """Dependency injection composition root."""

    def __init__(
        self,
        *,
        config_loader: ConfigLoaderPortABC | None = None,
        config_resolver: ConfigPathResolverPortABC | None = None,
        infrastructure_factory: InfrastructureFactoryPortABC | None = None,
        observability_factory: ObservabilityFactoryPortABC | None = None,
        abc_resolver: ABCRegistryResolverPortABC | None = None,
    ):
        # Lazy initialization - adapters created only when needed
        self._config_loader = config_loader
        self._config_resolver = config_resolver
        self._infrastructure_factory = infrastructure_factory
        self._observability_factory = observability_factory
        self._abc_resolver = abc_resolver

    def get_config_loader(self) -> ConfigLoaderPortABC:
        if self._config_loader is None:
            # Lazy import adapter only when actually needed
            from bioetl.infrastructure.adapters.config_loader_adapter import (
                ConfigLoaderAdapter,
            )
            self._config_loader = ConfigLoaderAdapter(
                self._get_schema_contract_provider()
            )
        return self._config_loader

    def get_config_resolver(self) -> ConfigPathResolverPortABC:
        if self._config_resolver is None:
            from bioetl.infrastructure.adapters.config_loader_adapter import (
                ConfigPathResolverAdapter,
            )
            self._config_resolver = ConfigPathResolverAdapter()
        return self._config_resolver

    def get_infrastructure_factory(self) -> InfrastructureFactoryPortABC:
        if self._infrastructure_factory is None:
            from bioetl.infrastructure.adapters.infrastructure_factory_adapter import (
                InfrastructureFactoryAdapter,
            )
            self._infrastructure_factory = InfrastructureFactoryAdapter()
        return self._infrastructure_factory

    def get_observability_factory(self) -> ObservabilityFactoryPortABC:
        if self._observability_factory is None:
            from bioetl.infrastructure.adapters.observability_factory_adapter import (
                ObservabilityFactoryAdapter,
            )
            self._observability_factory = ObservabilityFactoryAdapter()
        return self._observability_factory
```

### Задача 2.4: Рефакторинг остальных interfaces файлов

| Файл | Действие |
|------|----------|
| `bootstrap_factory.py` | Использовать `ConfigLoaderPortABC` |
| `factories/infrastructure.py` | Удалить, функционал в `CompositionRoot` |
| `factories/observability.py` | Удалить, функционал в `CompositionRoot` |
| `cli/app.py` | Использовать `CompositionRoot` |
| `use_case_factory.py` | Использовать порты из `CompositionRoot` |
| `application_context.py` | Получать зависимости из `CompositionRoot` |
| `monitoring/__init__.py` | Использовать `ObservabilityFactoryPortABC` |

### Критерии готовности Фазы 2

- [ ] Все порты созданы в `application/ports/`
- [ ] Все адаптеры созданы в `infrastructure/adapters/`
- [ ] `CompositionRoot` использует только порты
- [ ] Interfaces импортирует только адаптеры через lazy initialization
- [ ] Количество разрешённых импортов infrastructure в interfaces: ≤3

---

## Фаза 3: Публичный API и инкапсуляция

**Приоритет:** Высокий
**Источник:** REFACTORING_PLAN_v5.md
**Решает:** B1, B2
**Время:** ~3.5 часа

### Задача 3.1: Создание модели результата

**Добавить в:** `src/bioetl/domain/models.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractOnlyResult:
    """Result of extract-only pipeline execution."""
    total_rows: int
    total_chunks: int
```

### Задача 3.2: Создание публичного метода в PipelineBase

**Файл:** `src/bioetl/application/pipelines/base.py`

```python
from bioetl.domain.models import ExtractOnlyResult


class PipelineBase(ABC):
    # ... существующий код ...

    def run_extract_only(self, **kwargs: Any) -> ExtractOnlyResult:
        """Execute only the extract stage and return statistics.

        This method provides a clean public API for extract-only mode,
        encapsulating the internal extraction logic.

        Args:
            **kwargs: Arguments passed to the extract stage.

        Returns:
            ExtractOnlyResult with row count and chunk count.
        """
        extract_callable = self._get_extract_callable()
        iterator = self._normalize_extract_result(extract_callable(**kwargs))

        total_rows = 0
        total_chunks = 0

        for chunk in iterator:
            if chunk is None:
                continue
            total_rows += len(chunk)
            total_chunks += 1

        return ExtractOnlyResult(
            total_rows=total_rows,
            total_chunks=max(total_chunks, 1),
        )
```

### Задача 3.3: Обновление orchestrator

**Файл:** `src/bioetl/application/orchestrator.py`

```python
# БЫЛО:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_callable = pipeline._get_extract_callable()  # noqa: SLF001
    iterator = pipeline._normalize_extract_result(
        extract_callable()
    )  # noqa: SLF001

    total_rows = 0
    total_chunks = 0
    for chunk in iterator:
        if chunk is None:
            continue
        total_rows += len(chunk)
        total_chunks += 1
    # ... построение RunResult

# СТАНЕТ:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_result = pipeline.run_extract_only()  # Публичный API!

    stage = StageResult(
        stage_name=StageName.EXTRACT,
        success=True,
        records_processed=extract_result.total_rows,
        chunks_processed=extract_result.total_chunks,
        duration_sec=0.0,
        errors=[],
    )

    return RunResult(
        run_id=context.run_id,
        success=True,
        entity_name=self._config.entity_name,
        row_count=extract_result.total_rows,
        # ...
    )
```

### Критерии готовности Фазы 3

- [ ] `ExtractOnlyResult` добавлен в `domain/models.py`
- [ ] Метод `run_extract_only()` добавлен в `PipelineBase`
- [ ] `PipelineOrchestrator` использует публичный API
- [ ] Ни один модуль в `application/` не обращается к приватным методам пайплайна
- [ ] Удалены комментарии `noqa: SLF001`
- [ ] Новый метод покрыт тестами

---

## Фаза 4: Централизация сервисов

**Приоритет:** Средний
**Источник:** docs/REFACTORING_PLAN.md
**Решает:** D3, D4
**Время:** ~4 часа

### Задача 4.1: Расширить контракты наблюдаемости

**Файл:** `src/bioetl/domain/observability/contracts.py`

```python
from abc import ABC, abstractmethod
from typing import Any, ContextManager
from dataclasses import dataclass


@dataclass(frozen=True)
class SpanContext:
    """Context for distributed tracing span."""
    trace_id: str
    span_id: str
    parent_span_id: str | None = None


class TracingPortABC(ABC):
    """Abstract port for distributed tracing."""

    @abstractmethod
    def start_span(
        self,
        name: str,
        *,
        parent: SpanContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> ContextManager[SpanContext]:
        """Start a new tracing span."""
        ...

    @abstractmethod
    def get_current_span(self) -> SpanContext | None:
        """Get current active span context."""
        ...


class ObservabilityContextABC(ABC):
    """Unified observability context combining logging, metrics, and tracing."""

    @property
    @abstractmethod
    def logger(self) -> LoggingPortABC:
        """Get logger instance."""
        ...

    @property
    @abstractmethod
    def metrics(self) -> MetricsPortABC:
        """Get metrics instance."""
        ...

    @property
    @abstractmethod
    def tracer(self) -> TracingPortABC | None:
        """Get tracer instance (optional)."""
        ...

    @abstractmethod
    def with_context(self, **kwargs) -> "ObservabilityContextABC":
        """Create child context with additional bound context."""
        ...
```

### Задача 4.2: ObservabilityService

**Файл:** `src/bioetl/application/services/observability_service.py`

```python
"""Unified observability service for application layer."""
from dataclasses import dataclass
from typing import Any

from bioetl.application.ports.observability_factory_port import (
    ObservabilityFactoryPortABC,
)
from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
    ObservabilityContextABC,
    TracingPortABC,
)


@dataclass
class ObservabilityContext(ObservabilityContextABC):
    """Concrete observability context implementation."""

    _logger: LoggingPortABC
    _metrics: MetricsPortABC
    _tracer: TracingPortABC | None
    _bound_context: dict[str, Any]

    @property
    def logger(self) -> LoggingPortABC:
        return self._logger.apply_bind(**self._bound_context)

    @property
    def metrics(self) -> MetricsPortABC:
        return self._metrics

    @property
    def tracer(self) -> TracingPortABC | None:
        return self._tracer

    def with_context(self, **kwargs) -> "ObservabilityContext":
        new_context = {**self._bound_context, **kwargs}
        return ObservabilityContext(
            _logger=self._logger,
            _metrics=self._metrics,
            _tracer=self._tracer,
            _bound_context=new_context,
        )


class ObservabilityService:
    """Service for creating and managing observability contexts."""

    def __init__(self, factory: ObservabilityFactoryPortABC):
        self._factory = factory
        self._logger: LoggingPortABC | None = None
        self._metrics: MetricsPortABC | None = None
        self._tracer: TracingPortABC | None = None

    def create_context(self, **initial_context) -> ObservabilityContext:
        """Create new observability context with optional initial bindings."""
        if self._logger is None:
            self._logger = self._factory.create_logger()
        if self._metrics is None:
            self._metrics = self._factory.create_metrics()
        if self._tracer is None:
            self._tracer = self._factory.create_tracer()

        return ObservabilityContext(
            _logger=self._logger,
            _metrics=self._metrics,
            _tracer=self._tracer,
            _bound_context=initial_context,
        )

    def create_pipeline_context(
        self,
        pipeline_id: str,
        run_id: str,
    ) -> ObservabilityContext:
        """Create context specifically for pipeline execution."""
        return self.create_context(
            pipeline_id=pipeline_id,
            run_id=run_id,
        )
```

### Задача 4.3: ConfigurationService

**Файл:** `src/bioetl/application/services/configuration_service.py`

```python
"""Centralized configuration service for application layer."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bioetl.application.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.domain.configs.pipeline import PipelineConfig


@dataclass(frozen=True)
class ConfigurationRequest:
    """Request for loading configuration."""
    pipeline_id: str | None = None
    config_path: Path | None = None
    profile: str | None = None
    cli_overrides: dict[str, Any] | None = None
    env_overrides: dict[str, Any] | None = None


class ConfigurationService:
    """Centralized service for all configuration operations."""

    def __init__(
        self,
        loader: ConfigLoaderPortABC,
        path_resolver: ConfigPathResolverPortABC,
    ):
        self._loader = loader
        self._path_resolver = path_resolver

    def load(self, request: ConfigurationRequest) -> PipelineConfig:
        """Load configuration based on request parameters."""
        if request.config_path:
            return self._loader.get_from_path(
                request.config_path,
                profile=request.profile,
                cli_overrides=request.cli_overrides,
            )

        if request.pipeline_id:
            return self._loader.get_by_id(
                request.pipeline_id,
                profile=request.profile,
                cli_overrides=request.cli_overrides,
                env_overrides=request.env_overrides,
            )

        raise ValueError("Either pipeline_id or config_path must be provided")

    def get_configs_root(self) -> Path:
        """Get root directory for configurations."""
        return self._path_resolver.get_configs_root()

    def list_available_pipelines(self) -> list[str]:
        """List all available pipeline IDs."""
        configs_root = self.get_configs_root()
        pipelines = []

        for provider_dir in configs_root.iterdir():
            if provider_dir.is_dir() and not provider_dir.name.startswith("_"):
                for config_file in provider_dir.glob("*.yaml"):
                    pipeline_id = f"{provider_dir.name}.{config_file.stem}"
                    pipelines.append(pipeline_id)

        return sorted(pipelines)
```

### Задача 4.4: Интеграция сервисов в CompositionRoot

**Обновить:** `src/bioetl/interfaces/composition_root.py`

```python
from bioetl.application.services.configuration_service import ConfigurationService
from bioetl.application.services.observability_service import ObservabilityService


class CompositionRoot:
    # ...

    def get_configuration_service(self) -> ConfigurationService:
        """Get centralized configuration service."""
        if self._configuration_service is None:
            self._configuration_service = ConfigurationService(
                loader=self.get_config_loader(),
                path_resolver=self.get_config_resolver(),
            )
        return self._configuration_service

    def get_observability_service(self) -> ObservabilityService:
        """Get centralized observability service."""
        if self._observability_service is None:
            self._observability_service = ObservabilityService(
                factory=self.get_observability_factory(),
            )
        return self._observability_service
```

### Критерии готовности Фазы 4

- [ ] Контракты наблюдаемости расширены (TracingPortABC, ObservabilityContextABC)
- [ ] `ObservabilityService` создан и интегрирован
- [ ] `ConfigurationService` создан и интегрирован
- [ ] Use cases используют ObservabilityService
- [ ] CLI использует ConfigurationService

---

## Фаза 5: Усиление архитектурных тестов

**Приоритет:** Высокий
**Источник:** REFACTORING_PLAN_v5.md + docs/REFACTORING_PLAN.md
**Решает:** D5, D6
**Время:** ~2.5 часа

### Задача 5.1: Тест на инфраструктурные импорты в application

**Файл:** `tests/architecture/test_layer_dependencies.py`

```python
# Whitelist: разрешённые инфраструктурные импорты
APPLICATION_ALLOWED_INFRA_IMPORTS: set[str] = set()  # Пустой — ничего не разрешено


def test_application_has_no_infrastructure_imports() -> None:
    """Verify application layer has no direct infrastructure imports.

    This is stricter than test_application_avoids_infrastructure_implementations
    which only checks for 'impl' modules. This test catches ANY infrastructure
    import.
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue

            # Проверяем whitelist
            if reference.module in APPLICATION_ALLOWED_INFRA_IMPORTS:
                continue

            violations.append(
                _format_violation(
                    file_path,
                    reference.lineno,
                    f"application must not import infrastructure "
                    f"(found {reference.module})",
                )
            )

    _assert_no_violations(violations)
```

### Задача 5.2: Тест на инфраструктурные импорты в interfaces

```python
INTERFACES_ALLOWED_INFRA_IMPORTS: dict[str, set[str]] = {
    # Only adapters allowed, and only in composition_root.py
    "composition_root.py": {
        "bioetl.infrastructure.adapters.config_loader_adapter",
        "bioetl.infrastructure.adapters.infrastructure_factory_adapter",
        "bioetl.infrastructure.adapters.observability_factory_adapter",
    }
}


def test_interfaces_has_limited_infrastructure_imports() -> None:
    """Verify interfaces layer only imports allowed infrastructure modules."""
    violations: list[str] = []

    for file_path in sorted(INTERFACES_ROOT.rglob("*.py")):
        allowed = INTERFACES_ALLOWED_INFRA_IMPORTS.get(file_path.name, set())

        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue
            if reference.module in allowed:
                continue

            violations.append(
                _format_violation(
                    file_path,
                    reference.lineno,
                    f"interfaces must not import infrastructure directly "
                    f"(found {reference.module})",
                )
            )

    _assert_no_violations(violations)
```

### Задача 5.3: Тест на приватные атрибуты

```python
import re

PRIVATE_ATTR_PATTERN = re.compile(r"\._[a-z_]+\(")  # Вызовы приватных методов


def test_no_cross_module_private_access() -> None:
    """Verify no module accesses private attributes of other modules.

    This catches patterns like:
    - pipeline._get_extract_callable()
    - service._internal_method()
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        content = file_path.read_text(encoding="utf-8")

        for line_no, line in enumerate(content.splitlines(), 1):
            # Пропускаем строки внутри класса (self._method)
            if "self._" in line:
                continue
            if "cls._" in line:
                continue

            # Ищем внешние обращения к приватным методам
            matches = PRIVATE_ATTR_PATTERN.findall(line)
            if matches:
                violations.append(
                    _format_violation(
                        file_path,
                        line_no,
                        f"cross-module private attribute access: {matches}",
                    )
                )

    _assert_no_violations(violations)
```

### Задача 5.4: Интеграция с ruff

**Обновить:** `pyproject.toml`

```toml
[tool.ruff.lint]
select = [
    # ... существующие правила
    "SLF001",  # Private member accessed
]

# Убрать из per-file-ignores:
# [tool.ruff.lint.per-file-ignores]
# "src/bioetl/application/orchestrator.py" = ["SLF001"]  # УДАЛИТЬ!
```

### Задача 5.5: Обновление .importlinter

**Файл:** `.importlinter`

```ini
[contract:interfaces_no_direct_infrastructure]
name = Interfaces layer must not import infrastructure directly
type = forbidden
source_modules = bioetl.interfaces
forbidden_modules = bioetl.infrastructure
ignore_imports =
    # ТОЛЬКО адаптеры разрешены для lazy initialization в CompositionRoot
    bioetl.interfaces.composition_root -> bioetl.infrastructure.adapters.config_loader_adapter
    bioetl.interfaces.composition_root -> bioetl.infrastructure.adapters.infrastructure_factory_adapter
    bioetl.interfaces.composition_root -> bioetl.infrastructure.adapters.observability_factory_adapter
```

### Критерии готовности Фазы 5

- [ ] Тест `test_application_has_no_infrastructure_imports` добавлен и проходит
- [ ] Тест `test_interfaces_has_limited_infrastructure_imports` добавлен и проходит
- [ ] Тест `test_no_cross_module_private_access` добавлен и проходит
- [ ] ruff правило SLF001 включено без исключений для orchestrator
- [ ] `.importlinter` обновлён с минимальными исключениями
- [ ] CI блокирует регресс

---

## Фаза 6: Устранение технического долга

**Приоритет:** Низкий
**Источник:** REFACTORING_PLAN_v4.md
**Решает:** C1, C2, C3
**Время:** ~9.5 часов

### Задача 6.1: Ликвидация глобального состояния ProviderRegistry

**Файл:** `src/bioetl/domain/provider_registry.py`

Удалить:
- `_PROVIDER_REGISTRY: ProviderRegistryABC | None = None`
- `set_provider_registry()`
- `get_provider_registry()`
- `default_provider_registry()`

Все места использования должны получать registry через DI.

### Задача 6.2: Вынос Pandera-зависимости из Domain

**Файл:** `src/bioetl/domain/schemas/generator.py`

Перенести динамические импорты Pandera/YAML в infrastructure.

### Задача 6.3: Сокращение ignore_imports в .importlinter

**Текущее количество:** 13 исключений
**Целевое количество:** ≤3

---

## Метрики и контроль

### Метрики качества

| Метрика | Текущее | Целевое | Команда проверки |
|---------|:-------:|:-------:|------------------|
| infrastructure импорты в application | 1 | 0 | `grep -rn "bioetl.infrastructure" src/bioetl/application/` |
| infrastructure импорты в interfaces | 26 | ≤3 | `grep -rn "bioetl.infrastructure" src/bioetl/interfaces/` |
| Приватные вызовы (cross-module) | 2 | 0 | `grep -rn "\._[a-z_]*(" src/bioetl/application/ \| grep -v "self\._"` |
| `noqa: SLF001` в orchestrator | 2 | 0 | `grep -c "noqa: SLF001" src/bioetl/application/orchestrator.py` |
| ignore_imports в .importlinter | 13 | ≤3 | Подсчёт строк |
| Архитектурные тесты | pass | pass | `pytest tests/architecture/ -v` |

### Покрытие портов

| Измерение | Целевое значение |
|-----------|------------------|
| Порты с адаптерами | 100% |
| Порты с unit-тестами | ≥80% |
| Адаптеры с интеграционными тестами | ≥60% |

### Наблюдаемость

| Измерение | До | После |
|-----------|-----|-------|
| Шаги с обязательным логированием | ~40% | ≥90% |
| Пайплайны с метриками | 0% | 100% |
| Use cases с трассировкой | 0% | ≥50% |

### Полная проверка

```bash
# Все проверки одной командой
pytest tests/architecture/ tests/project_rules/ -v && \
grep -rn "bioetl.infrastructure" src/bioetl/application/ && \
grep -rn "noqa: SLF001" src/bioetl/application/ && \
lint-imports
```

---

## План выполнения

```
═══════════════════════════════════════════════════════════════════════════
                         ОБЩИЙ ПЛАН ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════

ФАЗА 1: Изоляция application от infrastructure (v5)         [3.5 ч]
├── 1.1 Удаление fallback в orchestrator
├── 1.2 Фабрика в composition root
├── 1.3 Обновление точек входа
└── 1.4 Обновление тестов

ФАЗА 2: Изоляция interfaces от infrastructure (v1)          [6 ч]
├── 2.1 Создание портов в application/ports/
├── 2.2 Создание адаптеров в infrastructure/adapters/
├── 2.3 Рефакторинг CompositionRoot
└── 2.4 Рефакторинг остальных interfaces файлов

ФАЗА 3: Публичный API и инкапсуляция (v5)                   [3.5 ч]
├── 3.1 Модель ExtractOnlyResult в domain
├── 3.2 Метод run_extract_only() в PipelineBase
└── 3.3 Обновление orchestrator

ФАЗА 4: Централизация сервисов (v1)                         [4 ч]
├── 4.1 Расширение контрактов наблюдаемости
├── 4.2 ObservabilityService
├── 4.3 ConfigurationService
└── 4.4 Интеграция в CompositionRoot

ФАЗА 5: Усиление архитектурных тестов (v5 + v1)             [2.5 ч]
├── 5.1 Тест на инфраструктурные импорты в application
├── 5.2 Тест на инфраструктурные импорты в interfaces
├── 5.3 Тест на приватные атрибуты
├── 5.4 Интеграция с ruff
└── 5.5 Обновление .importlinter

ФАЗА 6: Устранение технического долга (v4)                  [9.5 ч]
├── 6.1 Глобальное состояние ProviderRegistry
├── 6.2 Pandera в Domain
└── 6.3 Сокращение ignore_imports

═══════════════════════════════════════════════════════════════════════════
                     ИТОГО: ~29 часов
═══════════════════════════════════════════════════════════════════════════

РЕКОМЕНДУЕМЫЙ ПОРЯДОК:
──────────────────────────────────────────────────────────────────────────
  Фаза 1 → Фаза 3 → Фаза 5 (частично) → Фаза 2 → Фаза 4 → Фаза 5 → Фаза 6

  Логика: сначала критические нарушения в application (v5), затем interfaces
  (v1), архитектурные тесты добавляются по мере готовности компонентов.
```

---

## Ожидаемые результаты

### Прогноз изменения оценок

| Категория | Текущая | После фаз 1-5 | После всех фаз | Δ |
|-----------|:-------:|:-------------:|:--------------:|:-:|
| Слоистая архитектура | 6.5 | 8 | 8.5 | +2 |
| Ports & Adapters | 6 | 7.5 | 8 | +2 |
| Границы модулей | 6 | 7.5 | 7.5 | +1.5 |
| Качество доменной модели | 7 | 7 | 7.5 | +0.5 |
| Контракты и конфигурация | 6 | 7 | 7 | +1 |
| Обработка ошибок | 6 | 6 | 6 | 0 |
| Тестирование и QA | 6 | 7 | 7.5 | +1.5 |
| Наблюдаемость | 5 | 7 | 7 | +2 |
| Сопровождаемость | 6 | 7 | 7.5 | +1.5 |

### Прогноз интегрального балла

| Этап | Балл |
|------|:----:|
| Текущий | 6.36 |
| После фаз 1-3 (критические) | ~7.0 |
| После фаз 1-5 | ~7.3 |
| После всех фаз | **7.5–7.8** |

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|:-----------:|:-------:|-----------|
| Поломка существующих вызовов orchestrator | Высокая | Среднее | Deprecation warnings на 1-2 релиза |
| Ложные срабатывания архитектурных тестов | Средняя | Низкое | Whitelist для допустимых случаев |
| Несовместимость с internal CLI | Средняя | Среднее | Обновить CLI вместе с composition root |
| Регрессии в тестах | Средняя | Среднее | Полный тест-сьют после каждой фазы |
| Усложнение DI | Низкая | Низкое | Документирование графа зависимостей |
| Потеря производительности | Низкая | Низкое | Lazy initialization адаптеров |

### Стратегия миграции

1. **Фаза deprecation:** Добавить warnings в устаревший код
   ```python
   warnings.warn(
       "Using default registry factory is deprecated. "
       "Pass provider_registry_factory explicitly.",
       DeprecationWarning,
       stacklevel=3,
   )
   ```

2. **Фаза обновления:** Обновить все точки входа на явный DI

3. **Фаза удаления:** Удалить deprecated код, сделать параметры обязательными

---

## Ссылки

- [docs/REFACTORING_PLAN.md](../REFACTORING_PLAN.md) — план v1 (interfaces layer)
- [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md) — план v5 (application layer)
- [REFACTORING_PLAN_v4.md](./REFACTORING_PLAN_v4.md) — план v4 (технический долг)
- [architecture.md](./architecture.md)
- [PipelineOrchestrator](../../src/bioetl/application/orchestrator.py)
- [PipelineBase](../../src/bioetl/application/pipelines/base.py)
- [CompositionRoot](../../src/bioetl/interfaces/composition_root.py)
- [test_layer_dependencies.py](../../tests/architecture/test_layer_dependencies.py)
