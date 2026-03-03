"""Pipeline Factory - consolidated module for pipeline and runner creation.

Contains GenericPipelineFactory, assemble_runner, build_pipeline_services,
and create_pipeline_with_services. Follows DI pattern with declarative
configuration and assembly in the composition layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext
from bioetl.composition.factories.data_source_factory import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    extract_dq_configs as _extract_dq_configs_impl,
)
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    extract_dq_output_paths as _extract_dq_output_paths_impl,
)
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    extract_single_dq_config as _extract_single_dq_config_impl,
)
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    get_layer_path as _get_layer_path_impl,
)
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    has_flat_structure as _has_flat_structure_impl,
)
from bioetl.composition.factories.pipeline_factory_runner_assembly import (
    assemble_runner_impl as _assemble_runner_impl,
)
from bioetl.composition.factories.services_factory import (
    BaseServicesFactory,
    ServicesBuilder,
)
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import (
    load_pipeline_config,
    load_pipeline_contract_policy,
    yaml_config_to_domain,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import (
        GoldFilterConfig,
        InputFilterConfig,
        SilverFilterConfig,
    )
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")


__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
    "create_pipeline_with_services",
]


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract entity_type from pipeline_name.

    Example: "chembl_activity" → "activity"

    Args:
        pipeline_name: Full pipeline name with provider prefix.

    Returns:
        Entity type suffix, or None if no underscore in name.
    """
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


# =============================================================================
# GenericPipelineFactory - Main factory class
# =============================================================================


class GenericPipelineFactory(Generic[TPipeline]):
    """Configurable factory for creating pipelines via constructor parameters.

    Attributes:
        pipeline_name: Unique name for the pipeline
        pipeline_class: The pipeline class to instantiate
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Pandera schema for Gold layer
        pandera_silver_schema: Pandera DataFrameModel class for Silver validation
    """

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: Any = None,  # Any: Pandera DataFrameModel (no common base type)
        pandera_silver_schema: Any = None,  # Any: Pandera DataFrameModel...
        data_source_creator: DataSourceCreator | None = None,
        transformer_class: type[BaseTransformer] | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            pipeline_name: Unique name for the pipeline (e.g., "chembl_activity").
            pipeline_class: The pipeline class to instantiate.
            provider: Data provider name (e.g., "chembl", "pubmed").
            silver_schema: Optional PyArrow schema for Silver layer validation.
            gold_schema: Pandera DataFrameModel class for Gold layer validation.
            pandera_silver_schema: Optional Pandera DataFrameModel class for Silver
                validation. If provided, PanderaSilverValidator is created and
                injected into SilverWriter.
            data_source_creator: Optional custom data source creator function.
                If None, looked up from DataSourceRegistry by provider.
            transformer_class: Optional transformer class for Bronze-to-Silver
                and Silver-to-Gold transformations.

        Raises:
            ValueError: If gold_schema is not provided.
        """
        if gold_schema is None:
            raise ValueError(
                f"gold_schema is required for pipeline '{pipeline_name}'. "
                "All Gold layer writes must have schema validation."
            )
        self.pipeline_name = pipeline_name
        self.pipeline_class = pipeline_class
        self.provider = provider
        self.silver_schema = silver_schema
        self.gold_schema = gold_schema
        self.pandera_silver_schema = pandera_silver_schema
        self.transformer_class = transformer_class

        # Use custom creator or look up from registry
        self._create_data_source = data_source_creator or DataSourceRegistry.get(
            provider
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ) -> BaseTransformer | None:
        """Create transformer instance if transformer_class is configured.

        Args:
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            silver_filters: Optional domain-level filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names.

        Returns:
            Configured transformer instance, or None if no transformer_class.
        """
        if self.transformer_class is None:
            return None

        return self.transformer_class(
            provider=self.provider,
            entity_type=_extract_entity_type(self.pipeline_name),
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create data source using the configured creator.

        Args:
            settings: Application settings with provider credentials and paths.
            pipeline_config: Pipeline YAML configuration with source settings.
            logger: Structured logger for observability.
            filter_config: Optional input filter configuration for restricting
                which records are fetched from the data source.

        Returns:
            Configured DataSourcePort implementation for the pipeline's provider.
        """
        return self._create_data_source(
            settings,
            pipeline_config,
            logger,
            filter_config,
            pipeline_name=self.pipeline_name,
        )

    def build_services(
        self,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineServices:
        """Build PipelineServices from settings.

        Delegates to the module-level ``build_pipeline_services`` function,
        injecting the factory's pipeline name and data source creator.

        Args:
            settings: Application settings with data paths and credentials.
            logger: Structured logger for observability.
            config: Pre-loaded pipeline YAML config. If None, loaded from disk
                by pipeline name.
            filter_config: Optional input filter configuration for the data source.
            tracer: Optional TracingPort for distributed tracing.
            dq_monitor: Optional data quality monitor for anomaly detection.

        Returns:
            Configured PipelineServices instance with data source, storage,
            metrics, and other shared services.
        """
        return build_pipeline_services(
            pipeline_name=self.pipeline_name,
            create_data_source_fn=self._create_data_source,
            settings=settings,
            logger=logger,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
        )

    def create_with_services(
        self,
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
    ) -> TPipeline:
        """Create pipeline instance with services and optional transformer.

        Loads configuration once and reuses it for both services and the pipeline.
        If a transformer_class is configured on the factory, creates and injects
        the transformer via DI.

        Args:
            run_id: Unique identifier for this pipeline run.
            runtime: Pipeline runtime configuration (run_type, resume, limits).
            settings: Application settings with data paths and credentials.
            logger: Structured logger for observability.
            config: Pre-loaded pipeline YAML config. If None, loaded from disk.
            filter_config: Optional input filter configuration for the data source.
            tracer: Optional TracingPort for distributed tracing.
            dq_monitor: Optional data quality monitor for anomaly detection.
            metrics: Optional MetricsPort for transformer observability.
            cached_bronze: Optional CachedBronzeContext for reading from Bronze
                cache instead of making API calls.

        Returns:
            Fully configured pipeline instance of type TPipeline, ready for
            execution via a PipelineRunner.
        """
        return cast(
            TPipeline,
            create_pipeline_with_services(
                pipeline_name=self.pipeline_name,
                pipeline_class=self.pipeline_class,
                provider=self.provider,
                create_data_source_fn=self._create_data_source,
                transformer_class=self.transformer_class,
                pandera_silver_schema=self.pandera_silver_schema,
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
            ),
        )

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        """Create a fully configured PipelineRunner with all components.

        This is the primary factory method that assembles the full execution
        graph. It creates the pipeline instance via ``create_with_services``,
        then delegates to ``assemble_runner`` which constructs:

        - **BatchExecutor**: Unified batch processing (Bronze/Silver/Gold writes).
        - **CheckpointManager**: Resume support for interrupted runs.
        - **LockManager**: Distributed locking with heartbeat and TTL.
        - **PreflightService**: Pre-run validation checks.
        - **PostrunService**: Post-run cleanup, DQ evaluation, and metadata.
        - **MedallionLifecycleService**: Silver/Gold layer lifecycle management.
        - **PipelineObserver**: Metrics and tracing for the run lifecycle.
        - **DataQualityService**: DQ rule evaluation and anomaly detection.

        Args:
            run_id: Unique identifier for this pipeline run.
            runtime: Pipeline runtime configuration (run_type, resume, limits,
                lock TTL, strict_gold_validation).
            settings: Application settings with data paths, credentials, and
                environment info.
            observability: Unified ObservabilityBundle providing logger, tracer,
                metrics, and dq_monitor.
            filter_config: Optional input filter configuration for restricting
                which records are fetched from the data source.
            config: Pre-loaded pipeline YAML config. If None, loaded from disk
                by pipeline name.
            cached_bronze: Optional CachedBronzeContext for reading from Bronze
                cache instead of making API calls.

        Returns:
            Fully initialized PipelineRunner ready for ``runner.run()`` execution.
        """
        # Load config once if not provided
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        # Create pipeline instance with services, tracer, metrics, and dq_monitor (O1)
        # Cast logger to LoggerPort - structlog.BoundLogger is runtime-compatible
        pipeline = self.create_with_services(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=observability.logger,
            config=yaml_config,
            filter_config=filter_config,
            tracer=observability.tracer,
            dq_monitor=observability.dq_monitor,
            metrics=observability.metrics,
            cached_bronze=cached_bronze,
        )

        # Delegate runner assembly to dedicated function
        return assemble_runner(
            pipeline=pipeline,
            observability=observability,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            strict_gold_validation=(
                runtime.strict_gold_validation
                if settings.env != "prod" or settings.test_mode
                else True
            ),
            yaml_config=yaml_config,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: Any = None,  # Any: Pandera DataFrameModel (no common base type)
    pandera_silver_schema: Any = None,  # Any: Pandera DataFrameModel...
    transformer_class: type[BaseTransformer] | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Convenience function for creating pipeline factories.

    Args:
        pipeline_name: Pipeline identifier.
        pipeline_class: Pipeline class.
        provider: Data provider name.
        silver_schema: Silver schema.
        gold_schema: Gold schema.
        pandera_silver_schema: Pandera silver schema.
        transformer_class: Transformer class.

    Returns:
        Newly created GenericPipelineFactory[TPipeline] instance.
    """
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        pandera_silver_schema=pandera_silver_schema,
        transformer_class=transformer_class,
    )


# =============================================================================
# Runner Assembly Functions
# =============================================================================


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
    silver_validator: Any = None,  # Any: SilverValidatorPort (optional lazy import)
) -> PipelineServices:
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
        Configured PipelineServices instance
    """
    pipeline_config = config or load_pipeline_config(pipeline_name)
    shared_metrics = BaseServicesFactory._create_metrics(settings)

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

    return BaseServicesFactory.create_common_services(
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
    pandera_silver_schema: Any = None,  # Any: Pandera DataFrameModel...
) -> BasePipeline:
    """Create pipeline instance with services.

    Loads config once and reuses it for both services and pipeline.
    If transformer_class is configured, creates and injects transformer via DI.

    Args:
        pipeline_name: Name of the pipeline
        pipeline_class: Pipeline class to instantiate
        provider: Data provider name
        create_data_source_fn: Data source creator function
        transformer_class: Optional transformer class for Bronze→Silver
        run_id: Unique identifier for this pipeline run
        runtime: Pipeline runtime configuration
        settings: Application settings
        logger: Structured logger
        config: Pre-loaded pipeline config (avoids duplicate I/O)
        filter_config: Optional input filter configuration
        tracer: Optional tracer for distributed tracing
        dq_monitor: Optional data quality monitor
        metrics: Optional metrics port for transformer observability
        cached_bronze: Optional CachedBronzeContext for reading from Bronze
                      cache instead of API.
        pandera_silver_schema: Optional Pandera DataFrameModel class for Silver
            validation. If provided, PanderaSilverValidator is created and
            injected into SilverWriter.

    Returns:
        Configured pipeline instance
    """
    yaml_config = config or load_pipeline_config(pipeline_name)
    entity = _extract_entity_type(pipeline_name) or pipeline_name

    # Create Silver validator from Pandera schema if provided (DI pattern)
    silver_validator = None
    if pandera_silver_schema is not None:
        from bioetl.infrastructure.validation.pandera_validator import (
            PanderaSilverValidator,
        )

        silver_validator = PanderaSilverValidator(pandera_silver_schema.to_schema())

    # Create RunContext with versioning metadata for MetadataCoordinator
    run_context = RunContext.create(
        run_id=run_id,
        run_type=runtime.run_type,
        started_at=datetime.now(UTC),
        provider=provider,
        entity=entity,
        pipeline_version=get_pipeline_version(yaml_config),
        git_commit=get_git_commit(),
        config_hash=compute_config_hash(yaml_config),
    )
    metadata_coordinator = MetadataCoordinator(run_context)

    services = build_pipeline_services(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        config=yaml_config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=cached_bronze,
        silver_validator=silver_validator,
    )

    config_loader = PipelineConfigLoader(
        Path("configs"), relaxed_dq=settings.pipeline.relaxed_dq
    )
    resolved_dq = config_loader.resolve_dq_config(yaml_config)
    domain_config = yaml_config_to_domain(yaml_config, resolved_dq_config=resolved_dq)

    # Create transformer via DI if configured (with observability)
    transformer = None
    if transformer_class is not None:
        identity_service = IdentityService(
            content_hash_include_fields=set(yaml_config.content_hash.include) or None,
            content_hash_exclude_fields=set(yaml_config.content_hash.exclude),
        )
        try:
            contract_policy = load_pipeline_contract_policy(
                provider, _extract_entity_type(pipeline_name)
            )
        except ValueError:
            contract_policy = None
        transformer = transformer_class(
            provider=provider,
            entity_type=_extract_entity_type(pipeline_name),
            tracer=tracer,
            metrics=metrics,
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            identity_service=identity_service,
            contract_policy=contract_policy,
        )

    return pipeline_class.create(
        run_id=run_id,
        runtime=runtime,
        services=services,
        config=domain_config,
        transformer=transformer,
    )


def assemble_runner(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: Any,  # Any: Pandera DataFrameModel (no common base type)
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a pipeline instance."""
    return _assemble_runner_impl(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        yaml_config=yaml_config,
        dq_configs_extractor=_extract_dq_configs,
    )


def _extract_single_dq_config(
    sink: Any,  # Any: dynamic Pydantic sink config (heterogeneous per pipeline)
    layer_name: str,
    config_class: Any,  # Any: Pydantic model class (layer-specific)
) -> Any | None:  # Any: DQ report config varies by layer
    """Extract DQ config for a single layer."""
    return _extract_single_dq_config_impl(sink, layer_name, config_class)


def _extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Extract DQ report configs from YAML."""
    return _extract_dq_configs_impl(yaml_config)


def _get_layer_path(config: Any) -> str | None:  # Any: dynamic sink layer config
    """Extract path from layer config if available."""
    return _get_layer_path_impl(config)


def _has_flat_structure(config: Any) -> bool:  # Any: dynamic sink layer config
    """Check if layer config has flat_structure enabled."""
    return _has_flat_structure_impl(config)


def _extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract DQ output paths and flat_structure from YAML config."""
    return _extract_dq_output_paths_impl(yaml_config)
