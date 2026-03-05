"""Service bundle wiring for pipeline instances."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.factories._observability_wiring import (
    _create_cached_bronze_data_source as _create_cached_bronze_data_source_impl,
)
from bioetl.composition.factories._observability_wiring import (
    _create_data_source as _create_data_source_impl,
)
from bioetl.composition.factories._observability_wiring import (
    create_shared_metrics,
)
from bioetl.composition.factories.data_source_factory import DataSourceCreator
from bioetl.composition.factories.pipeline_factory_construction import (
    DomainConfigResolver,
    RunContextFactory,
    TransformerBuilder,
)
from bioetl.composition.factories.services_factory import BaseServicesFactory
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.services.versioning import (
    compute_config_hash as _compute_config_hash_direct,
)
from bioetl.composition.services.versioning import (
    get_git_commit,
    get_pipeline_version,
)
from bioetl.infrastructure.config import (
    load_pipeline_config as _load_pipeline_config_direct,
)
from bioetl.infrastructure.config import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config import (
    yaml_config_to_domain as _yaml_config_to_domain_direct,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.composition.factories.pipeline_factory_construction import (
        DomainConfigMapper,
    )
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


class _SchemaBuilder(Protocol):
    """Protocol for schema classes exposing ``to_schema``."""

    @classmethod
    def to_schema(cls) -> object:
        """Materialize schema representation."""
        ...


__all__ = [
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "build_pipeline_services",
    "create_pipeline_with_services",
]


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline config via direct infrastructure dependency."""
    return _load_pipeline_config_direct(pipeline_name)


def yaml_config_to_domain(
    yaml_config: PipelineYamlConfig,
    resolved_dq_config: DQConfig | None = None,
) -> PipelineConfig:
    """Map YAML config via direct infrastructure dependency."""
    return _yaml_config_to_domain_direct(
        yaml_config=yaml_config,
        resolved_dq_config=resolved_dq_config,
    )


def compute_config_hash(
    config: PipelineYamlConfig | dict[str, object],
) -> str:
    """Compute config hash via direct versioning dependency."""
    return _compute_config_hash_direct(config)


@dataclass(frozen=True, slots=True)
class ServiceBundleDependencies:
    """Explicit dependencies for service bundle runtime wiring."""

    load_pipeline_config: Callable[[str], PipelineYamlConfig]
    yaml_config_to_domain: Callable[
        [PipelineYamlConfig, DQConfig | None], PipelineConfig
    ]
    compute_config_hash: Callable[[PipelineYamlConfig | dict[str, object]], str]
    base_services_factory: type[BaseServicesFactory]


def _resolve_service_bundle_dependencies(
    override: ServiceBundleDependencies | None = None,
) -> ServiceBundleDependencies:
    """Resolve runtime dependencies with optional explicit override."""
    if override is not None:
        return override

    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config,
        yaml_config_to_domain=yaml_config_to_domain,
        compute_config_hash=compute_config_hash,
        base_services_factory=BaseServicesFactory,
    )


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract trailing entity from `<provider>_<entity>` pipeline names."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


def _create_data_source(
    create_data_source_fn: DataSourceCreator,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Compatibility wrapper around observability data-source wiring."""
    return _create_data_source_impl(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def _create_cached_bronze_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    cached_bronze: CachedBronzeContext,
) -> DataSourcePort:
    """Compatibility wrapper for cached Bronze data-source factory."""
    return _create_cached_bronze_data_source_impl(
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        cached_bronze=cached_bronze,
    )


def build_pipeline_services(
    pipeline_name: str,
    create_data_source_fn: DataSourceCreator,
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
    """Build shared pipeline services with optional cached-bronze mode."""
    deps = _resolve_service_bundle_dependencies(_deps)
    pipeline_config = config or deps.load_pipeline_config(pipeline_name)
    base_services_factory = deps.base_services_factory
    shared_metrics = create_shared_metrics(
        settings=settings,
        base_services_factory=base_services_factory,
    )
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
    else:
        data_source = _create_data_source(
            create_data_source_fn=create_data_source_fn,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=shared_metrics,
            pipeline_name=pipeline_name,
        )

    return base_services_factory.create_common_services(
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


def create_pipeline_with_services(
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreator,
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
    """Create pipeline instance with services and optional transformer."""
    return _create_pipeline_with_services_impl(
        _PipelineCreationInputs(
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
        ),
        deps=_resolve_service_bundle_dependencies(_deps),
    )


@dataclass(frozen=True, slots=True)
class _PipelineCreationInputs:
    pipeline_name: str
    pipeline_class: type[BasePipeline]
    provider: str
    create_data_source_fn: DataSourceCreator
    transformer_class: type[BaseTransformer] | None
    run_id: RunID
    runtime: RuntimeConfig
    settings: Settings
    logger: LoggerPort
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None
    metrics: MetricsPort | None = None
    cached_bronze: CachedBronzeContext | None = None
    pandera_silver_schema: object | None = None


def _create_pipeline_with_services_impl(
    inputs: _PipelineCreationInputs,
    *,
    deps: ServiceBundleDependencies,
) -> BasePipeline:
    """Implement pipeline construction for ``create_pipeline_with_services``."""
    yaml_config = inputs.config or deps.load_pipeline_config(inputs.pipeline_name)
    run_context_factory = RunContextFactory(
        pipeline_name=inputs.pipeline_name,
        provider=inputs.provider,
        entity_type_extractor=_extract_entity_type,
        pipeline_version_getter=get_pipeline_version,
        git_commit_getter=get_git_commit,
        config_hash_getter=deps.compute_config_hash,
    )
    metadata_coordinator = MetadataCoordinator(
        run_context_factory.create(
            run_id=inputs.run_id,
            runtime=inputs.runtime,
            yaml_config=yaml_config,
        )
    )

    services = build_pipeline_services(
        pipeline_name=inputs.pipeline_name,
        create_data_source_fn=inputs.create_data_source_fn,
        settings=inputs.settings,
        logger=inputs.logger,
        config=yaml_config,
        filter_config=inputs.filter_config,
        tracer=inputs.tracer,
        dq_monitor=inputs.dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=inputs.cached_bronze,
        silver_validator=_create_silver_validator(inputs.pandera_silver_schema),
    )
    domain_config = DomainConfigResolver(
        configs_root=Path("configs"),
        loader_class=PipelineConfigLoader,
        domain_mapper=cast("DomainConfigMapper", deps.yaml_config_to_domain),
    ).resolve(
        yaml_config,
        relaxed_dq=inputs.settings.pipeline.relaxed_dq,
    )
    transformer = TransformerBuilder(
        provider=inputs.provider,
        pipeline_name=inputs.pipeline_name,
        entity_type_extractor=_extract_entity_type,
        contract_policy_loader=load_pipeline_contract_policy,
    ).build(
        transformer_class=inputs.transformer_class,
        yaml_config=yaml_config,
        domain_config=domain_config,
        tracer=inputs.tracer,
        metrics=inputs.metrics,
    )

    return inputs.pipeline_class.create(
        run_id=inputs.run_id,
        runtime=inputs.runtime,
        services=services,
        config=domain_config,
        transformer=transformer,
    )


def _create_silver_validator(
    pandera_silver_schema: object | None,
) -> SilverValidatorPort | None:
    """Create Pandera silver validator when schema is configured."""
    if pandera_silver_schema is None:
        return None

    from bioetl.infrastructure.validation.pandera_validator import (
        PanderaSilverValidator,
    )

    schema_builder = cast(_SchemaBuilder, pandera_silver_schema)
    typed_schema = cast("pa.DataFrameSchema | None", schema_builder.to_schema())
    return PanderaSilverValidator(typed_schema)
