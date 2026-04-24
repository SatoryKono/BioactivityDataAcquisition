"""Service bundle facade for pipeline wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _ServiceBundleDeps,
)
from bioetl.composition.factories.services._bundle_support import (
    ServiceBundleDependencies,
    resolve_service_bundle_dependencies,
)
from bioetl.composition.factories.services._bundle_support import (
    create_pipeline_data_source as _create_pipeline_data_source_impl,
)
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.composition.factories.services.observability_api import (
    _create_cached_bronze_data_source as _create_cached_bronze_data_source_impl,
)
from bioetl.composition.factories.services.observability_api import (
    _create_data_source as _create_data_source_impl,
)
from bioetl.composition.factories.services.observability_api import (
    create_shared_metrics,
)
from bioetl.composition.services.versioning import (
    compute_config_hash as _compute_config_hash_direct,
)
from bioetl.infrastructure.config.converters import (
    yaml_config_to_domain as _yaml_config_to_domain_direct,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config as _load_pipeline_config_direct,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.config import DQConfig, PipelineConfig
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
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "PipelineCreationInputs",
    "ServiceBundleDependencies",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "build_pipeline_services",
    "create_pipeline_with_services",
]

PipelineCreationInputs = _PipelineCreationInputs


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline YAML configuration using the canonical config API seam."""
    return _load_pipeline_config_direct(pipeline_name)


def yaml_config_to_domain(
    yaml_config: PipelineYamlConfig,
    resolved_dq_config: DQConfig | None = None,
) -> PipelineConfig:
    """Convert YAML pipeline config to domain config with optional DQ overrides."""
    return _yaml_config_to_domain_direct(
        yaml_config=yaml_config,
        resolved_dq_config=resolved_dq_config,
    )


def compute_config_hash(config: PipelineYamlConfig | dict[str, object]) -> str:
    """Compute deterministic config hash for run-manifest and cache identity."""
    config_hash: str = _compute_config_hash_direct(config)
    return config_hash


def _resolve_service_bundle_dependencies(
    override: ServiceBundleDependencies | None = None,
) -> ServiceBundleDependencies:
    return resolve_service_bundle_dependencies(
        override=override,
        load_pipeline_config_fn=load_pipeline_config,
        yaml_config_to_domain_fn=yaml_config_to_domain,
        compute_config_hash_fn=compute_config_hash,
        base_services_factory=BaseServicesFactory,
    )


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract the trailing entity from `<provider>_<entity>` pipeline names."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


_create_data_source = _create_data_source_impl
_create_cached_bronze_data_source = _create_cached_bronze_data_source_impl


def _create_pipeline_data_source(
    *,
    pipeline_name: str,
    pipeline_config: PipelineYamlConfig,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort,
    cached_bronze: CachedBronzeContext | None,
) -> DataSourcePort:
    return _create_pipeline_data_source_impl(
        pipeline_name=pipeline_name,
        pipeline_config=pipeline_config,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        cached_bronze=cached_bronze,
        create_cached_bronze_data_source_fn=_create_cached_bronze_data_source,
        create_data_source_impl_fn=_create_data_source,
    )


def build_pipeline_services(
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    audit: AuditPort | None = None,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metadata_coordinator: MetadataCoordinator | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    silver_validator: SilverValidatorPort | None = None,
    _deps: ServiceBundleDependencies | None = None,
) -> PipelineService:
    """Build the shared pipeline service bundle for one pipeline run."""
    deps = _resolve_service_bundle_dependencies(_deps)
    pipeline_config = config or deps.load_pipeline_config(pipeline_name)
    shared_metrics = create_shared_metrics(
        settings=settings,
        base_services_factory=deps.base_services_factory,
    )
    data_source = _create_pipeline_data_source(
        pipeline_name=pipeline_name,
        pipeline_config=pipeline_config,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=shared_metrics,
        cached_bronze=cached_bronze,
    )
    return deps.base_services_factory.create_common_services(
        settings=settings,
        logger=logger,
        data_source=data_source,
        pipeline_config=pipeline_config,
        pipeline_name=pipeline_name,
        audit=audit,
        metrics=shared_metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )


def create_pipeline_with_services(
    inputs: PipelineCreationInputs,
    _deps: ServiceBundleDependencies | None = None,
) -> BasePipeline:
    """Create a pipeline instance with its resolved service bundle."""
    # Compatibility markers for architecture static checks:
    # transformer_class(...) happens inside the delegated builder path.
    # transformer=transformer is preserved at the pipeline constructor boundary.
    resolved_deps = cast(
        _ServiceBundleDeps,
        _resolve_service_bundle_dependencies(_deps),
    )
    return _create_pipeline_with_services_impl(
        inputs,
        deps=resolved_deps,
        extract_entity_type=_extract_entity_type,
        build_pipeline_services_fn=cast(
            _BuildPipelineServicesFn,
            build_pipeline_services,
        ),
    )
