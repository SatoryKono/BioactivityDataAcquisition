"""Private support helpers for service-bundle wiring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.factories.pipeline.creation_support import (
        _PipelineCreationInputs,
        _PipelineCreationRequest,
    )
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        AuditPort,
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.config.domain_config_resolver import DomainConfigMapper
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


@dataclass(frozen=True, slots=True)
class ServiceBundleDependencies:
    """Explicit dependency set for service-bundle wiring."""

    load_pipeline_config: Callable[[str], PipelineYamlConfig]
    yaml_config_to_domain: DomainConfigMapper
    compute_config_hash: Callable[[PipelineYamlConfig | dict[str, object]], str]
    base_services_factory: BaseServicesFactoryProtocol


def resolve_service_bundle_dependencies(
    *,
    override: ServiceBundleDependencies | None,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    yaml_config_to_domain_fn: DomainConfigMapper,
    compute_config_hash_fn: Callable[[PipelineYamlConfig | dict[str, object]], str],
    base_services_factory: BaseServicesFactoryProtocol,
) -> ServiceBundleDependencies:
    """Resolve runtime dependencies with an optional test override."""
    if override is not None:
        return override
    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config_fn,
        yaml_config_to_domain=yaml_config_to_domain_fn,
        compute_config_hash=compute_config_hash_fn,
        base_services_factory=base_services_factory,
    )


def create_pipeline_data_source(
    *,
    pipeline_name: str,
    pipeline_config: PipelineYamlConfig,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort,
    cached_bronze: CachedBronzeContext | None,
    create_cached_bronze_data_source_fn: Callable[..., DataSourcePort],
    create_data_source_impl_fn: Callable[..., DataSourcePort],
) -> DataSourcePort:
    """Resolve live-vs-cached data source construction for one pipeline run."""
    from bioetl.composition.factories.services.observability_api import (
        create_data_source_with_observability,
    )

    return create_data_source_with_observability(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        shared_metrics=metrics,
        pipeline_name=pipeline_name,
        cached_bronze=cached_bronze,
        create_cached_bronze_data_source_fn=create_cached_bronze_data_source_fn,
        create_data_source_impl_fn=create_data_source_impl_fn,
    )


@dataclass(frozen=True, slots=True)
class _PipelineCreationIdentity:
    """Immutable identity bundle for pipeline creation input assembly."""

    pipeline_name: str
    pipeline_class: type[BasePipeline]
    provider: str
    create_data_source_fn: DataSourceCreatorProtocol
    transformer_class: type[BaseTransformer] | None
    pandera_silver_schema: object | None


def build_pipeline_creation_inputs(
    *,
    identity: _PipelineCreationIdentity,
    request: _PipelineCreationRequest,
) -> _PipelineCreationInputs:
    """Build the delegated pipeline-creation envelope."""
    from bioetl.composition.factories.pipeline.creation_support import (
        _PipelineCreationInputs,
    )

    return _PipelineCreationInputs(
        pipeline_name=identity.pipeline_name,
        pipeline_class=identity.pipeline_class,
        provider=identity.provider,
        create_data_source_fn=identity.create_data_source_fn,
        transformer_class=identity.transformer_class,
        request=request,
        pandera_silver_schema=identity.pandera_silver_schema,
    )
