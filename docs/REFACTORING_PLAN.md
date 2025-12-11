# План рефакторинга архитектуры BioETL

**Версия:** 1.0
**Дата:** 2025-12-11
**Текущий интегральный балл:** 6.8/10
**Целевой интегральный балл:** ≥7.5/10

---

## Содержание

1. [Резюме](#резюме)
2. [Фаза 1: Изоляция интерфейсного слоя от инфраструктуры](#фаза-1-изоляция-интерфейсного-слоя-от-инфраструктуры)
3. [Фаза 2: Централизация наблюдаемости](#фаза-2-централизация-наблюдаемости)
4. [Фаза 3: Централизация конфигурационных политик](#фаза-3-централизация-конфигурационных-политик)
5. [Фаза 4: Расширение архитектурных тестов](#фаза-4-расширение-архитектурных-тестов)
6. [Метрики и контроль регресса](#метрики-и-контроль-регресса)

---

## Резюме

### Выявленные архитектурные нарушения

| Файл | Количество нарушений |
|------|---------------------|
| `interfaces/composition_root.py` | 10 |
| `interfaces/bootstrap_factory.py` | 2 |
| `interfaces/factories/infrastructure.py` | 4 |
| `interfaces/factories/observability.py` | 2 |
| `interfaces/cli/app.py` | 2 |
| `interfaces/use_case_factory.py` | 2 |
| `interfaces/application_context.py` | 1 |
| `interfaces/monitoring/__init__.py` | 3 |
| **Итого** | **26 прямых импортов** |

### Цели рефакторинга

1. **Устранить 26 прямых зависимостей** interfaces → infrastructure
2. **Ввести единый слой наблюдаемости** с портами в domain/application
3. **Централизовать конфигурационные политики** в application слое
4. **Расширить архитектурные тесты** для интерфейсного слоя

---

## Фаза 1: Изоляция интерфейсного слоя от инфраструктуры

**Приоритет:** Критический
**Ожидаемый эффект:** Ports & Adapters +1 балл

### Задача 1.1: Создать порты фабрик в application слое

**Цель:** Вынести контракты фабрик из infrastructure в application

**Новые файлы:**

```
src/bioetl/application/
├── ports/
│   ├── __init__.py
│   ├── config_loader_port.py      # ConfigLoaderPortABC
│   ├── infrastructure_factory_port.py  # InfrastructureFactoryPortABC
│   └── observability_factory_port.py   # ObservabilityFactoryPortABC
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

---

### Задача 1.2: Создать адаптеры фабрик в infrastructure слое

**Цель:** Реализовать порты из application как адаптеры

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

**Файл:** `src/bioetl/infrastructure/adapters/infrastructure_factory_adapter.py`

```python
"""Infrastructure adapter for factory port."""
from bioetl.application.ports.infrastructure_factory_port import (
    ABCRegistryResolverPortABC,
    InfrastructureFactoryPortABC,
)
from bioetl.domain.clients.base.contracts import HttpClientABC, RateLimiterABC
from bioetl.infrastructure.clients.base.abc_registry_resolver import ABCRegistryResolver
from bioetl.infrastructure.clients.base.factories import (
    build_http_client,
    create_rate_limiter,
)


class InfrastructureFactoryAdapter(InfrastructureFactoryPortABC):
    """Adapter implementing infrastructure factory port."""

    def create_http_client(self, base_url: str, **kwargs) -> HttpClientABC:
        return build_http_client(base_url=base_url, **kwargs)

    def create_rate_limiter(
        self, requests_per_second: float, **kwargs
    ) -> RateLimiterABC:
        return create_rate_limiter(requests_per_second, **kwargs)


class ABCRegistryResolverAdapter(ABCRegistryResolverPortABC):
    """Adapter implementing ABC registry resolver port."""

    def __init__(self, yaml_path: str | None = None):
        self._resolver = ABCRegistryResolver(yaml_path)

    def resolve(self, abc_name: str) -> type:
        return self._resolver.resolve(abc_name)

    def resolve_instance(self, abc_name: str, **kwargs) -> object:
        cls = self._resolver.resolve(abc_name)
        return cls(**kwargs)
```

**Файл:** `src/bioetl/infrastructure/adapters/observability_factory_adapter.py`

```python
"""Infrastructure adapter for observability factory port."""
from bioetl.application.ports.observability_factory_port import (
    ObservabilityFactoryPortABC,
)
from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
    TracingPortABC,
)
from bioetl.infrastructure.observability.factories import (
    create_logging_port,
    create_metrics_port,
)


class ObservabilityFactoryAdapter(ObservabilityFactoryPortABC):
    """Adapter implementing observability factory port."""

    def create_logger(self) -> LoggingPortABC:
        return create_logging_port()

    def create_metrics(self) -> MetricsPortABC:
        return create_metrics_port()

    def create_tracer(self) -> TracingPortABC | None:
        # Tracing not yet implemented
        return None
```

---

### Задача 1.3: Рефакторинг CompositionRoot

**Цель:** Убрать прямые импорты infrastructure, использовать порты

**Файл:** `src/bioetl/interfaces/composition_root.py`

**Изменения:**

```python
# БЫЛО (26 прямых импортов infrastructure):
from bioetl.infrastructure.config.loader import SchemaContractLoader
from bioetl.infrastructure.config.sources import get_configs_root
from bioetl.infrastructure.clients.base.factories import build_http_client
# ... ещё 23 импорта

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

    # ... остальные методы используют фабрики вместо прямых импортов
```

---

### Задача 1.4: Рефакторинг CLI

**Цель:** CLI работает только через CompositionRoot/порты

**Файл:** `src/bioetl/interfaces/cli/app.py`

**Изменения:**

```python
# БЫЛО:
from bioetl.infrastructure.config.sources import get_configs_root

@app.command()
def run(pipeline: str, ...):
    configs_root = get_configs_root()  # Прямой вызов infrastructure
    ...

# СТАНЕТ:
from bioetl.interfaces.composition_root import get_composition_root

@app.command()
def run(pipeline: str, ...):
    root = get_composition_root()
    configs_root = root.get_config_resolver().get_configs_root()
    ...
```

---

### Задача 1.5: Рефакторинг остальных interfaces файлов

**Файлы для рефакторинга:**

| Файл | Действие |
|------|----------|
| `bootstrap_factory.py` | Использовать `ConfigLoaderPortABC` |
| `factories/infrastructure.py` | Удалить, функционал в `CompositionRoot` |
| `factories/observability.py` | Удалить, функционал в `CompositionRoot` |
| `use_case_factory.py` | Использовать порты из `CompositionRoot` |
| `application_context.py` | Получать зависимости из `CompositionRoot` |
| `monitoring/__init__.py` | Использовать `ObservabilityFactoryPortABC` |

---

## Фаза 2: Централизация наблюдаемости

**Приоритет:** Высокий
**Ожидаемый эффект:** Наблюдаемость +2 балла

### Задача 2.1: Расширить контракты наблюдаемости

**Файл:** `src/bioetl/domain/observability/contracts.py`

**Добавить:**

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

### Задача 2.2: Создать unified observability service

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

### Задача 2.3: Интегрировать наблюдаемость в use cases

**Файл:** `src/bioetl/application/use_cases/__init__.py`

**Изменения:**

```python
from bioetl.application.services.observability_service import ObservabilityService


class RunPipelineUseCase:
    def __init__(
        self,
        *,
        config_loader: ConfigLoaderPortABC,
        orchestrator: PipelineOrchestrator,
        observability: ObservabilityService,
    ):
        self._config_loader = config_loader
        self._orchestrator = orchestrator
        self._observability = observability

    def execute(self, request: RunPipelineRequest) -> RunPipelineResponse:
        # Create pipeline-scoped observability context
        obs_ctx = self._observability.create_pipeline_context(
            pipeline_id=request.pipeline_id,
            run_id=request.run_id or self._generate_run_id(),
        )

        obs_ctx.logger.info(
            "Pipeline execution started",
            profile=request.profile,
            dry_run=request.dry_run,
        )

        obs_ctx.metrics.increment(
            "pipeline_executions_total",
            labels={"pipeline": request.pipeline_id},
        )

        try:
            config = self._config_loader.get_by_id(
                request.pipeline_id,
                profile=request.profile,
                cli_overrides=request.overrides,
            )

            result = self._orchestrator.run(config, obs_ctx)

            obs_ctx.logger.info(
                "Pipeline execution completed",
                records_processed=result.records_processed,
                duration_seconds=result.duration_seconds,
            )

            return RunPipelineResponse(success=True, result=result)

        except Exception as e:
            obs_ctx.logger.error(
                "Pipeline execution failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            obs_ctx.metrics.increment(
                "pipeline_errors_total",
                labels={"pipeline": request.pipeline_id, "error_type": type(e).__name__},
            )
            raise
```

---

## Фаза 3: Централизация конфигурационных политик

**Приоритет:** Средний
**Ожидаемый эффект:** Конфигурация +1 балл

### Задача 3.1: Создать ConfigurationService в application

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
    """
    Centralized service for all configuration operations.

    Encapsulates:
    - Config loading (by ID or path)
    - Profile resolution
    - Override merging
    - Path resolution
    """

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

    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        """Resolve configuration file path for pipeline ID."""
        return self._path_resolver.resolve_pipeline_path(pipeline_id)

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

### Задача 3.2: Интегрировать ConfigurationService

**Файл:** `src/bioetl/interfaces/composition_root.py`

**Добавить:**

```python
from bioetl.application.services.configuration_service import ConfigurationService


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
```

### Задача 3.3: Обновить CLI для использования ConfigurationService

**Файл:** `src/bioetl/interfaces/cli/app.py`

```python
@app.command()
def list_pipelines():
    """List all available pipelines."""
    root = get_composition_root()
    config_service = root.get_configuration_service()

    pipelines = config_service.list_available_pipelines()
    console.print(f"Available pipelines ({len(pipelines)}):")
    for pipeline_id in pipelines:
        console.print(f"  - {pipeline_id}")


@app.command()
def run(
    pipeline: str,
    profile: str | None = None,
    config_path: Path | None = None,
    dry_run: bool = False,
    **overrides,
):
    """Run a pipeline."""
    root = get_composition_root()
    config_service = root.get_configuration_service()

    request = ConfigurationRequest(
        pipeline_id=pipeline if not config_path else None,
        config_path=config_path,
        profile=profile,
        cli_overrides=overrides,
    )

    config = config_service.load(request)
    # ... proceed with pipeline execution
```

---

## Фаза 4: Расширение архитектурных тестов

**Приоритет:** Средний
**Ожидаемый эффект:** Тестирование архитектуры сохраняется на 8

### Задача 4.1: Добавить правило interfaces → infrastructure

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

### Задача 4.2: Создать тест на отсутствие прямых импортов

**Файл:** `tests/architecture/test_interfaces_isolation.py`

```python
"""Tests ensuring interfaces layer isolation from infrastructure."""
import ast
from pathlib import Path

import pytest

INTERFACES_DIR = Path("src/bioetl/interfaces")
ALLOWED_INFRA_IMPORTS = {
    # Only adapters allowed, and only in composition_root.py
    "composition_root.py": {
        "bioetl.infrastructure.adapters.config_loader_adapter",
        "bioetl.infrastructure.adapters.infrastructure_factory_adapter",
        "bioetl.infrastructure.adapters.observability_factory_adapter",
    }
}


def get_infrastructure_imports(file_path: Path) -> set[str]:
    """Extract all infrastructure imports from a Python file."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    infra_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "infrastructure" in alias.name:
                    infra_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and "infrastructure" in node.module:
                infra_imports.add(node.module)

    return infra_imports


def test_interfaces_has_no_direct_infrastructure_imports():
    """Verify interfaces layer doesn't import infrastructure directly."""
    violations = []

    for py_file in INTERFACES_DIR.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        relative_name = py_file.name
        infra_imports = get_infrastructure_imports(py_file)
        allowed = ALLOWED_INFRA_IMPORTS.get(relative_name, set())

        forbidden = infra_imports - allowed
        if forbidden:
            violations.append((py_file, forbidden))

    if violations:
        msg = "Interfaces layer has forbidden infrastructure imports:\n"
        for file_path, imports in violations:
            msg += f"\n  {file_path}:\n"
            for imp in imports:
                msg += f"    - {imp}\n"
        pytest.fail(msg)


def test_interfaces_only_uses_application_ports():
    """Verify interfaces imports go through application ports."""
    required_port_usage = {
        "composition_root.py": {
            "ConfigLoaderPortABC",
            "InfrastructureFactoryPortABC",
            "ObservabilityFactoryPortABC",
        }
    }

    for file_name, expected_ports in required_port_usage.items():
        file_path = INTERFACES_DIR / file_name
        if not file_path.exists():
            continue

        content = file_path.read_text()
        missing = {port for port in expected_ports if port not in content}

        if missing:
            pytest.fail(
                f"{file_name} missing required port imports: {missing}"
            )
```

### Задача 4.3: Добавить тест покрытия портов

**Файл:** `tests/architecture/test_port_coverage.py`

```python
"""Tests ensuring all ports have implementations and tests."""
import importlib
import inspect
from pathlib import Path

import pytest

PORTS_DIR = Path("src/bioetl/application/ports")
ADAPTERS_DIR = Path("src/bioetl/infrastructure/adapters")


def get_abc_classes(module_path: Path) -> list[str]:
    """Get all ABC class names from a module."""
    spec = importlib.util.spec_from_file_location("mod", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return [
        name for name, obj in inspect.getmembers(module, inspect.isclass)
        if name.endswith("ABC") or name.endswith("Protocol")
    ]


def test_all_ports_have_adapters():
    """Every port ABC should have corresponding adapter."""
    port_abcs = set()
    for port_file in PORTS_DIR.glob("*.py"):
        if port_file.name.startswith("_"):
            continue
        port_abcs.update(get_abc_classes(port_file))

    adapter_content = ""
    for adapter_file in ADAPTERS_DIR.glob("*.py"):
        adapter_content += adapter_file.read_text()

    missing = []
    for abc_name in port_abcs:
        # Adapter should implement the ABC
        impl_name = abc_name.replace("ABC", "Adapter").replace("Protocol", "Adapter")
        if impl_name not in adapter_content and abc_name not in adapter_content:
            missing.append(abc_name)

    if missing:
        pytest.fail(f"Ports without adapters: {missing}")
```

---

## Метрики и контроль регресса

### Метрика 1: Архитектурные нарушения

| Измерение | До рефакторинга | После |
|-----------|-----------------|-------|
| interfaces → infrastructure импорты | 26 | 3* |
| application → infrastructure.impl | 0 | 0 |
| domain → внешние слои | 0 | 0 |

*3 разрешённых импорта адаптеров в composition_root.py

### Метрика 2: Покрытие портов

| Измерение | Целевое значение |
|-----------|------------------|
| Порты с адаптерами | 100% |
| Порты с unit-тестами | ≥80% |
| Адаптеры с интеграционными тестами | ≥60% |

### Метрика 3: Наблюдаемость

| Измерение | До | После |
|-----------|-----|-------|
| Шаги с обязательным логированием | ~40% | ≥90% |
| Пайплайны с метриками | 0% | 100% |
| Use cases с трассировкой | 0% | ≥50% |

### Метрика 4: Конфигурация

| Измерение | Целевое значение |
|-----------|------------------|
| Единая точка загрузки конфигов | ConfigurationService |
| Тесты резолва путей | 100% покрытие |
| Smoke-тесты конфигураций | 0 ошибок |

---

## Ожидаемый результат

### Изменение интегрального балла

| Категория | До | После | Δ |
|-----------|-----|-------|---|
| Слоистая архитектура | 7 | 7 | 0 |
| Ports & Adapters | 6 | 7 | +1 |
| Модульность | 7 | 7 | 0 |
| Доменная модель | 7 | 7 | 0 |
| Конфигурация | 6 | 7 | +1 |
| Тестирование архитектуры | 8 | 8 | 0 |
| Обработка ошибок | 7 | 7 | 0 |
| Документация | 8 | 8 | 0 |
| Наблюдаемость | 5 | 7 | +2 |
| Технический долг | 6 | 7 | +1 |

**Итоговый интегральный балл:** 6.8 → **7.5** (+0.7)

---

## Порядок выполнения

```
Фаза 1 (Критично) ─────────────────────────────────────────
  1.1 Создать порты в application/ports/
  1.2 Создать адаптеры в infrastructure/adapters/
  1.3 Рефакторинг CompositionRoot
  1.4 Рефакторинг CLI
  1.5 Рефакторинг остальных interfaces файлов

Фаза 2 (Высокий приоритет) ────────────────────────────────
  2.1 Расширить контракты наблюдаемости
  2.2 Создать ObservabilityService
  2.3 Интегрировать в use cases

Фаза 3 (Средний приоритет) ────────────────────────────────
  3.1 Создать ConfigurationService
  3.2 Интегрировать в CompositionRoot
  3.3 Обновить CLI

Фаза 4 (Средний приоритет) ────────────────────────────────
  4.1 Обновить .importlinter
  4.2 Добавить test_interfaces_isolation.py
  4.3 Добавить test_port_coverage.py
```

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Регрессии в тестах | Средняя | Запускать полный тест-сьют после каждой фазы |
| Усложнение DI | Низкая | Документировать граф зависимостей |
| Потеря производительности | Низкая | Lazy initialization адаптеров |
| Несовместимость с legacy | Средняя | Сохранить deprecated shims на 1-2 версии |
