"""Pipeline factory compatibility-only facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs as _extract_dq_configs,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_output_paths as _extract_dq_output_paths,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_single_dq_config as _extract_single_dq_config,
)
from bioetl.composition.factories.dq.context_resolver import (
    get_layer_path as _get_layer_path,
)
from bioetl.composition.factories.dq.context_resolver import (
    has_flat_structure as _has_flat_structure,
)
from bioetl.composition.factories.pipeline._service_bundle_compat import (
    _BUILD_PIPELINE_SERVICES_WARNING,
    _CREATE_PIPELINE_WITH_SERVICES_WARNING,
    BaseServicesFactory,
    ServiceBundleDependencies,
    _resolve_compat_service_bundle_dependencies,
    _warn_compatibility,
    compute_config_hash,
    load_pipeline_config,
    yaml_config_to_domain,
)
from bioetl.composition.factories.pipeline.pipeline_assembler import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.composition.factories.services.bundle import (
    _create_cached_bronze_data_source,
    _create_data_source,
)
from bioetl.composition.factories.services.bundle import (
    build_pipeline_services as _build_pipeline_services,
)
from bioetl.composition.factories.services.bundle import (
    create_pipeline_with_services as _create_pipeline_with_services,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.services.metadata_coordinator import MetadataCoordinator
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

# Keep explicit references so static analyzers treat legacy re-exports as used.
_LEGACY_REEXPORTS = (
    _extract_dq_configs,
    _extract_dq_output_paths,
    _extract_single_dq_config,
    _get_layer_path,
    _has_flat_structure,
    _create_cached_bronze_data_source,
    _create_data_source,
)


def build_pipeline_services(
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metadata_coordinator: MetadataCoordinator | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    silver_validator: SilverValidatorPort | None = None,
    _deps: ServiceBundleDependencies | None = None,
) -> PipelineService:
    """Deprecated compatibility wrapper over canonical service-bundle wiring."""
    _warn_compatibility(_BUILD_PIPELINE_SERVICES_WARNING)
    return _build_pipeline_services(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        config=config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=cached_bronze,
        silver_validator=silver_validator,
        _deps=_resolve_compat_service_bundle_dependencies(_deps),
    )


def create_pipeline_with_services(
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    pandera_silver_schema: object | None = None,
    _deps: ServiceBundleDependencies | None = None,
) -> BasePipeline:
    """Deprecated compatibility wrapper over canonical pipeline construction."""
    _warn_compatibility(_CREATE_PIPELINE_WITH_SERVICES_WARNING)
    return _create_pipeline_with_services(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        create_data_source_fn=create_data_source_fn,
        transformer_class=transformer_class,
        run_id=run_id,
        runtime=runtime,
        settings=settings,
        logger=logger,
        config=config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metrics=metrics,
        cached_bronze=cached_bronze,
        pandera_silver_schema=pandera_silver_schema,
        _deps=_resolve_compat_service_bundle_dependencies(_deps),
    )


__all__ = [
    "BaseServicesFactory",
    "GenericPipelineFactory",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "_extract_dq_configs",
    "_extract_dq_output_paths",
    "_extract_single_dq_config",
    "_get_layer_path",
    "_has_flat_structure",
    "assemble_runner",
    "build_pipeline_services",
    "compute_config_hash",
    "create_pipeline_factory",
    "create_pipeline_with_services",
    "load_pipeline_config",
    "yaml_config_to_domain",
]
