"""Pipeline construction ports migrated from composition (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.ports import (  # type: ignore[attr-defined]
    DomainConfigMapper,
    EntityTypeExtractor,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )

    CachedBronzeContext = object
    ContractPolicyProtocol = object
    InputFilterConfig = object
    MetadataCoordinator = object
    PipelineService = object
    PipelineYamlConfig = object
    RunLedgerService = object
    Settings = object

__all__ = [
    "BaseServicesFactoryProtocol",
    "ContractPolicyLoaderProtocol",
    "DomainConfigMapper",
    "EntityTypeExtractor",
    "PipelineRunnerProtocol",
    "RegistryEntryProtocol",
    "SchemaBuilderProtocol",
]


@runtime_checkable
class ContractPolicyLoaderProtocol(Protocol):
    """Callable contract for loading pipeline contract policy."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyProtocol: ...


@runtime_checkable
class SchemaBuilderProtocol(Protocol):
    """Protocol for schema classes that can materialize a runtime schema."""

    @classmethod
    def to_schema(cls) -> object: ...


@runtime_checkable
class RegistryEntryProtocol(Protocol):
    """Structural fields required by registry-manifest validation."""

    pipeline_name: str
    provider: str
    entity_type: str
    transformer_class: object | None
    gold_schema: object | None
    pandera_silver_schema: object | None


@runtime_checkable
class BaseServicesFactoryProtocol(Protocol):
    """Class-like service factory surface used by lazy composition seams."""

    def _create_metrics(self, settings: Settings) -> MetricsPort: ...

    def create_common_services(
        self,
        settings: Settings,
        logger: LoggerPort,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
        pipeline_name: str,
        audit: AuditPort | None = None,
        metrics: MetricsPort | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> PipelineService: ...


@runtime_checkable
class PipelineRunnerProtocol(Protocol):
    """Minimal runner contract required for ledger collaborator attachment."""

    services: object

    def attach_run_ledger_service(self, service: RunLedgerService) -> None: ...
