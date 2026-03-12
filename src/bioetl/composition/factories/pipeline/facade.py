"""Pipeline Factory - backward-compatibility re-export facade.

All implementation has been extracted to:
- pipeline_assembler.py: GenericPipelineFactory, assemble_runner, create_pipeline_factory
- service_bundle_factory.py: build_pipeline_services, create_pipeline_with_services
- dq_context_resolver.py: DQ config extraction helpers
"""

from __future__ import annotations

import warnings
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
from bioetl.composition.factories.pipeline.pipeline_assembler import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.composition.factories.services.bundle import (
    ServiceBundleDependencies,
    _create_cached_bronze_data_source,
    _create_data_source,
)
from bioetl.composition.factories.services.bundle import (
    build_pipeline_services as _build_pipeline_services,
)
from bioetl.composition.factories.services.bundle import (
    create_pipeline_with_services as _create_pipeline_with_services,
)
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.composition.services.versioning import compute_config_hash
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
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

_BUILD_PIPELINE_SERVICES_WARNING = (
    "Use bioetl.composition.factories.services.bundle.build_pipeline_services "
    "for direct wiring. pipeline_factory facade remains for compatibility."
)
_CREATE_PIPELINE_WITH_SERVICES_WARNING = (
    "Use bioetl.composition.factories.services.bundle.create_pipeline_with_services "
    "for direct wiring. pipeline_factory facade remains for compatibility."
)

_DEFAULT_COMPAT_SERVICE_BUNDLE_DEPENDENCIES = ServiceBundleDependencies(
    load_pipeline_config=load_pipeline_config,
    yaml_config_to_domain=yaml_config_to_domain,
    compute_config_hash=compute_config_hash,
    base_services_factory=BaseServicesFactory,
)


def _resolve_compat_service_bundle_dependencies(
    deps: ServiceBundleDependencies | None = None,
) -> ServiceBundleDependencies:
    """Resolve compatibility dependencies bound to facade-visible symbols."""
    return deps or _DEFAULT_COMPAT_SERVICE_BUNDLE_DEPENDENCIES


def _warn_compatibility(message: str) -> None:
    """Emit a deprecation warning for legacy pipeline factory entrypoints."""
    warnings.warn(
        message,
        DeprecationWarning,
        stacklevel=3,
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
    """Compatibility facade delegating to service_bundle_factory implementation.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity').
        create_data_source_fn: Callable that creates the provider data source.
        settings: Application settings for infrastructure wiring.
        logger: LoggerPort for structured logging.
        config: Optional pre-loaded pipeline YAML config; loaded from disk if None.
        filter_config: Optional input filter configuration; disables filtering if None.
        tracer: Optional TracingPort for distributed tracing.
        dq_monitor: Optional DQMonitorPort for data quality monitoring.
        metadata_coordinator: Optional coordinator for pipeline metadata writes.
        cached_bronze: Optional cached Bronze context; uses live API if None.
        silver_validator: Optional Silver layer validator (required in production).
        _deps: Optional dependency overrides for testing; resolved from defaults if None.

    Returns:
        Fully wired PipelineService bundle for the pipeline run.
    """
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
    """Compatibility facade delegating to service_bundle_factory implementation.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity').
        pipeline_class: Concrete pipeline class to instantiate.
        provider: Provider name (e.g., 'chembl').
        create_data_source_fn: Callable that creates the provider data source.
        transformer_class: Optional transformer class; no transformer used if None.
        run_id: Unique identifier for this pipeline run.
        runtime: Runtime configuration (run type, limits, vacuum settings).
        settings: Application settings for infrastructure wiring.
        logger: LoggerPort for structured logging.
        config: Optional pre-loaded pipeline YAML config; loaded from disk if None.
        filter_config: Optional input filter configuration; disables filtering if None.
        tracer: Optional TracingPort for distributed tracing.
        dq_monitor: Optional DQMonitorPort for data quality monitoring.
        metrics: Optional MetricsPort for metrics collection.
        cached_bronze: Optional cached Bronze context; uses live API if None.
        pandera_silver_schema: Optional Pandera DataFrameModel for Silver validation.
        _deps: Optional dependency overrides for testing; resolved from defaults if None.

    Returns:
        Configured BasePipeline instance ready for execution.
    """
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
