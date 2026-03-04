"""Service Bundle Factory.

Creates PipelineService and pipeline instances with services.
Extracted from pipeline_factory.py for composition layer LOC compliance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.factories.data_source_factory import DataSourceCreator
from bioetl.composition.factories.pipeline_factory_construction import (
    DomainConfigResolver,
    RunContextFactory,
    TransformerBuilder,
)
from bioetl.composition.factories.services_factory import BaseServicesFactory
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.services.versioning import (
    get_git_commit,
    get_pipeline_version,
)
from bioetl.infrastructure.config import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.config import RuntimeConfig
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
    "build_pipeline_services",
    "create_pipeline_with_services",
]


def load_pipeline_config(pipeline_name: str):
    """Load pipeline config via pipeline_factory facade for patch compatibility."""
    from bioetl.composition.factories import pipeline_factory

    return pipeline_factory.load_pipeline_config(pipeline_name)


def yaml_config_to_domain(*args, **kwargs):
    """Map YAML config via pipeline_factory facade for patch compatibility."""
    from bioetl.composition.factories import pipeline_factory

    return pipeline_factory.yaml_config_to_domain(*args, **kwargs)


def compute_config_hash(*args, **kwargs):
    """Compute config hash via pipeline_factory facade for patch compatibility."""
    from bioetl.composition.factories import pipeline_factory

    return pipeline_factory.compute_config_hash(*args, **kwargs)


_DEFAULT_BASE_SERVICES_FACTORY = BaseServicesFactory


def _resolve_base_services_factory():
    """Resolve BaseServicesFactory with dual-path patch compatibility."""
    if BaseServicesFactory is not _DEFAULT_BASE_SERVICES_FACTORY:
        return BaseServicesFactory

    from bioetl.composition.factories import pipeline_factory

    return pipeline_factory.BaseServicesFactory


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract entity_type from pipeline_name.

    Example: "chembl_activity" -> "activity"

    Args:
        pipeline_name: Full pipeline name with provider prefix.

    Returns:
        Entity type suffix, or None if no underscore in name.
    """
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
    """Create data source using the provided creator function.

    Args:
        create_data_source_fn: Data source creator function
        settings: Application settings
        pipeline_config: Pipeline configuration
        logger: Structured logger
        filter_config: Optional filter configuration
        metrics: Optional metrics port for provider-level observability.
        pipeline_name: Pipeline name for logging context

    Returns:
        Configured DataSourcePort
    """
    return create_data_source_fn(
        settings,
        pipeline_config,
        logger,
        filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def _create_cached_bronze_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    cached_bronze: CachedBronzeContext,
) -> DataSourcePort:
    """Create CachedBronzeDataSource for reading from Bronze cache.

    Creates a data source that reads from existing Bronze layer files
    instead of making API calls. Used when cached_bronze mode is enabled.

    Args:
        settings: Application settings (for resolving base paths).
        pipeline_config: Pipeline configuration (for provider/entity).
        logger: Structured logger.
        cached_bronze: CachedBronzeContext with path/date settings.

    Returns:
        CachedBronzeDataSource implementing DataSourcePort.
    """
    from bioetl.domain.ports import NoOpMetrics
    from bioetl.infrastructure.adapters import CachedBronzeDataSource
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    provider = pipeline_config.provider
    entity_type = pipeline_config.entity_type

    # Resolve Bronze path: explicit or convention-based
    if cached_bronze.bronze_path:
        bronze_path = Path(cached_bronze.bronze_path)
    else:
        # Convention: data/output/bronze/{provider}/{entity_type}
        bronze_path = settings.bronze_path / provider / entity_type

    # Create BronzeWriter as reader (reusing read_bronze/list_batches methods)
    # flat_structure=True because convention path already includes provider/entity
    bronze_reader = BronzeWriter(
        base_path=bronze_path,
        logger=logger,
        metrics=NoOpMetrics(),
        flat_structure=True,
    )

    return CachedBronzeDataSource(
        bronze_reader=bronze_reader,
        provider=provider,
        entity_type=entity_type,
        logger=logger,
        bronze_date=cached_bronze.bronze_date,
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
) -> PipelineService:
    """Build shared pipeline services using DI container.

    Args:
        pipeline_name: Name of the pipeline
        create_data_source_fn: Data source creator function
        settings: Application settings
        logger: Structured logger
        config: Pre-loaded pipeline config (avoids duplicate I/O)
        filter_config: Optional input filter configuration
        tracer: Optional tracer (created via bootstrap_tracer_port())
        dq_monitor: Optional data quality monitor for anomaly detection
        metadata_coordinator: Optional MetadataCoordinator for centralized
                            metadata creation across Bronze, Silver, Gold.
        cached_bronze: Optional CachedBronzeContext for reading from Bronze
                      cache instead of API. When enabled, creates
                      CachedBronzeDataSource instead of the normal data source.
        silver_validator: Optional SilverValidatorPort for Pandera validation
            in SilverWriter. Created from Pandera Silver schema.

    Returns:
        Configured PipelineService instance
    """
    pipeline_config = config or load_pipeline_config(pipeline_name)
    base_services_factory = _resolve_base_services_factory()
    shared_metrics = base_services_factory._create_metrics(settings)

    # Choose data source based on cached_bronze mode
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
            create_data_source_fn,
            settings,
            pipeline_config,
            logger,
            filter_config,
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
        )
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
) -> BasePipeline:
    """Implement pipeline construction for ``create_pipeline_with_services``."""
    yaml_config = inputs.config or load_pipeline_config(inputs.pipeline_name)
    run_context_factory = RunContextFactory(
        pipeline_name=inputs.pipeline_name,
        provider=inputs.provider,
        entity_type_extractor=_extract_entity_type,
        pipeline_version_getter=get_pipeline_version,
        git_commit_getter=get_git_commit,
        config_hash_getter=compute_config_hash,
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
        domain_mapper=yaml_config_to_domain,
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
