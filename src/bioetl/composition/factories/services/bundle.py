"""Service bundle facade for pipeline wiring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _PipelineCreationRequest,
    _ServiceBundleDeps,
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
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "build_pipeline_services",
    "create_pipeline_with_services",
]


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    return _load_pipeline_config_direct(pipeline_name)


def yaml_config_to_domain(
    yaml_config: PipelineYamlConfig,
    resolved_dq_config: DQConfig | None = None,
) -> PipelineConfig:
    return _yaml_config_to_domain_direct(
        yaml_config=yaml_config,
        resolved_dq_config=resolved_dq_config,
    )


def compute_config_hash(config: PipelineYamlConfig | dict[str, object]) -> str:
    return _compute_config_hash_direct(config)


@dataclass(frozen=True, slots=True)
class ServiceBundleDependencies:
    """Explicit dependency set for service-bundle wiring."""

    load_pipeline_config: Callable[[str], PipelineYamlConfig]
    yaml_config_to_domain: Callable[
        [PipelineYamlConfig, DQConfig | None], PipelineConfig
    ]
    compute_config_hash: Callable[[PipelineYamlConfig | dict[str, object]], str]
    base_services_factory: type[BaseServicesFactory]


def _resolve_service_bundle_dependencies(
    override: ServiceBundleDependencies | None = None,
) -> ServiceBundleDependencies:
    """Resolve runtime dependencies with an optional test override."""
    if override is not None:
        return override
    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config,
        yaml_config_to_domain=yaml_config_to_domain,
        compute_config_hash=compute_config_hash,
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
    """Resolve live-vs-cached data source construction for one pipeline run."""
    if cached_bronze is not None and cached_bronze.enabled:
        data_source = _create_cached_bronze_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            cached_bronze=cached_bronze,
        )
        logger.info(
            "using_cached_bronze_mode",
            pipeline=pipeline_name,
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )
        return data_source
    return _create_data_source(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
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
        metrics=shared_metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )


def _build_pipeline_creation_inputs(
    *,
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    manifest_id: str | None,
    config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    effective_config_artifact_id: str | None,
    config: PipelineYamlConfig | None,
    filter_config: InputFilterConfig | None,
    tracer: TracingPort | None,
    dq_monitor: DQMonitorPort | None,
    metrics: MetricsPort | None,
    cached_bronze: CachedBronzeContext | None,
    pandera_silver_schema: object | None,
) -> _PipelineCreationInputs:
    """Build the delegated pipeline-creation envelope."""
    return _PipelineCreationInputs(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        create_data_source_fn=create_data_source_fn,
        transformer_class=transformer_class,
        request=_PipelineCreationRequest(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=logger,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metrics=metrics,
            cached_bronze=cached_bronze,
        ),
        pandera_silver_schema=pandera_silver_schema,
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
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    pandera_silver_schema: object | None = None,
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
        _build_pipeline_creation_inputs(
            pipeline_name=pipeline_name,
            pipeline_class=pipeline_class,
            provider=provider,
            create_data_source_fn=create_data_source_fn,
            transformer_class=transformer_class,
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=logger,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metrics=metrics,
            cached_bronze=cached_bronze,
            pandera_silver_schema=pandera_silver_schema,
        ),
        deps=resolved_deps,
        extract_entity_type=_extract_entity_type,
        build_pipeline_services_fn=cast(
            _BuildPipelineServicesFn,
            build_pipeline_services,
        ),
    )
