"""Factory/bootstrap structural contracts (ADR-058)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.ports.pipeline_registry import PipelineRegistryProtocol
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.quality.quarantine_service import (
        QuarantineService,
    )
    from bioetl.domain.ports import (
        AuditPort,
        DQMonitorPort,
        LoggerPort,
        TracingPort,
    )

    from .health import HealthListenerDependenciesProtocol

    CachedBronzeContext = object
    DataSourceCreatorProtocol = object
    DomainConfigMapperPort = object
    InputFilterConfig = object
    MetadataCoordinator = object
    PipelineService = object
    PipelineYamlConfig = object
    Settings = object
    SilverValidatorPort = object
    _CreatePipelineWithServicesRequest = object


class ObservabilityApiModule(Protocol):
    """Typed subset of the public observability API."""

    def start_metrics_server(
        self,
        port: int = 8000,
        addr: str = "0.0.0.0",
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        logger: LoggerPort | None = None,
    ) -> bool:
        """Start the Prometheus metrics HTTP server."""
        ...


class ServiceBundleDeps(Protocol):
    """Subset of dependencies required by pipeline creation internals."""

    @property
    def load_pipeline_config(self) -> Callable[[str], PipelineYamlConfig]:
        """Load YAML pipeline configuration by name."""
        ...

    @property
    def yaml_config_to_domain(self) -> DomainConfigMapperPort:
        """Mapper from YAML pipeline config to domain config."""
        ...

    @property
    def compute_config_hash(
        self,
    ) -> Callable[[PipelineYamlConfig | dict[str, object]], str]:
        """Stable hash of a pipeline configuration payload."""
        ...


class BuildPipelineServicesFn(Protocol):
    """Typed callback for constructing the service bundle."""

    def __call__(
        self,
        pipeline_name: str,
        create_data_source_fn: DataSourceCreatorProtocol,
        settings: Settings,
        logger: LoggerPort,
        audit: AuditPort | None,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        cached_bronze: CachedBronzeContext | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> PipelineService: ...


class FactoryLike(Protocol):
    """Structural factory surface used by pipeline construction internals."""

    @property
    def pipeline_name(self) -> str:
        """Registered pipeline name for this factory."""
        ...

    @property
    def _create_data_source(self) -> DataSourceCreatorProtocol: ...

    @property
    def pipeline_class(self) -> type[object]:
        """Pipeline class constructed by this factory."""
        ...

    @property
    def provider(self) -> str:
        """Provider identifier bound to this factory."""
        ...

    @property
    def transformer_class(self) -> type[object] | None:
        """Optional transformer class for this factory."""
        ...

    @property
    def pandera_silver_schema(self) -> object | None:
        """Optional Pandera Silver schema for this factory."""
        ...

    def create_with_services(
        self,
        request: _CreatePipelineWithServicesRequest,
    ) -> object:
        """Construct a pipeline instance with an injected service bundle."""
        ...


class LoggerBindableObservability(Protocol):
    logger: object


class QuarantineServiceFactoryProtocol(Protocol):
    """Build the quarantine administration service for one data root."""

    def __call__(
        self,
        *,
        data_root: Path | None = None,
    ) -> QuarantineService: ...


class PipelineRunnerServiceFactoryProtocol(Protocol):
    """Build the pipeline runner service from an explicit registry."""

    def __call__(
        self,
        registry: PipelineRegistryProtocol,
    ) -> PipelineRunnerService: ...


class HealthServerDependenciesFactoryProtocol(Protocol):
    """Build health-server dependencies for one data root."""

    def __call__(
        self,
        *,
        data_root: Path | None = None,
    ) -> HealthListenerDependenciesProtocol: ...
