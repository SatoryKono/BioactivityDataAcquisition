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

        Raises:
            ValueError: If gold_schema is not provided
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
        """Create data source using the configured creator."""
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
        """Build PipelineServices from settings."""
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
        """Create pipeline instance with services and optional transformer."""
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
        """Create a fully configured PipelineRunner with all components."""
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
    """Convenience function for creating pipeline factories."""
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
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create data source using the provided creator function.

    Args:
        create_data_source_fn: Data source creator function
        settings: Application settings
        pipeline_config: Pipeline configuration
        logger: Structured logger
        filter_config: Optional filter configuration
        pipeline_name: Pipeline name for logging context

    Returns:
        Configured DataSourcePort
    """
    return create_data_source_fn(
        settings, pipeline_config, logger, filter_config, pipeline_name=pipeline_name
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
    from pathlib import Path

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
            pipeline_name=pipeline_name,
        )

    return BaseServicesFactory.create_common_services(
        settings=settings,
        logger=logger,
        data_source=data_source,
        pipeline_config=pipeline_config,
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
    """Assemble a PipelineRunner from a pipeline instance.

    Handles construction of the pipeline execution graph using BatchExecutor.
    Services are created directly here (DI pattern).

    Args:
        pipeline: Configured pipeline instance
        observability: Unified observability bundle (logger, tracer, metrics, dq_monitor)
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Schema for Gold layer validation
        strict_gold_validation: Whether to enforce strict Gold validation
        yaml_config: Original YAML config for DQ report extraction

    Returns:
        Fully initialized PipelineRunner
    """
    # Create Helper Components using ServicesBuilder
    logger_port = observability.logger

    # Cast loading_strategy since __post_init__ converts str to LoadingStrategy enum
    checkpoint_manager = ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
        loading_strategy=cast(LoadingStrategy | None, pipeline.config.loading_strategy),
    )

    # Create lifecycle service (M5)
    lifecycle_service = MedallionLifecycleService(
        storage=pipeline.services.storage,
        logger=logger_port,
    )

    # Create shared LockContextHolder to pass context from LockManager to RecordProcessor
    context_holder = LockContextHolder()

    # Create application services directly (DI pattern, no intermediate bundle)
    lock_manager = LockManager.create(
        lock_port=pipeline.services.lock,
        run_id=pipeline.context.run_id,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        run_type=pipeline.runtime.run_type,
        lock_ttl=pipeline.runtime.effective_lock_ttl,
        wait_for_lock=pipeline.runtime.wait_for_lock,
        wait_timeout=pipeline.runtime.lock_wait_timeout,
        heartbeat_interval=pipeline.runtime.heartbeat_interval,
        logger=logger_port,
        shutdown_signal=pipeline.shutdown_signal,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )

    preflight_service = PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=logger_port,
        metrics=pipeline.services.metrics,
    )

    # Create DataQualityService for DQ evaluation
    dq_service = DataQualityService(
        dq_monitor=pipeline.services.dq_monitor,
        config=pipeline.config.dq,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
        entity_type=pipeline.config.entity_type,
    )

    # Extract DQ configs from YAML config for DQ report generation
    dq_configs = _extract_dq_configs(yaml_config)

    postrun_service = PostrunService(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        storage=pipeline.services.storage,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        metadata_coordinator=pipeline.services.metadata_coordinator,
        metadata_writer=pipeline.services.metadata_writer,
        # DQ Report parameters
        dq_report_service=pipeline.services.dq_report_service,
        bronze_dq_config=dq_configs.bronze,
        silver_dq_config=dq_configs.silver,
        gold_dq_config=dq_configs.gold,
    )

    observer = PipelineObserver(
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.context.run_id,
        run_type=pipeline.runtime.run_type,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        tracer=observability.tracer,
    )

    # Extract sink paths for DQ report generation
    dq_output_paths = _extract_dq_output_paths(yaml_config)

    # Create unified BatchExecutor (replaces PipelineExecutor + RecordProcessor)
    # Safety Guard §4.6: lock validation via lock_validator callback
    batch_executor = ServicesBuilder.create_batch_executor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_manager.validate,
        tracer=observability.tracer,
        # DQ report output paths for flat_structure support
        bronze_output_path=dq_output_paths.bronze_path,
        silver_output_path=dq_output_paths.silver_path,
        gold_output_path=dq_output_paths.gold_path,
        flat_structure=dq_output_paths.flat_structure,
    )

    # Assemble Runner with directly injected services (explicit DI)
    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=batch_executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=logger_port,
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
        pipeline=pipeline,
        tracer=observability.tracer,
    )


def _extract_single_dq_config(
    sink: Any,  # Any: dynamic Pydantic sink config (heterogeneous per pipeline)
    layer_name: str,
    config_class: Any,  # Any: Pydantic model class (...
) -> Any | None:  # Any: DQ report config varies by layer
    """Extract DQ config for a single layer.

    Args:
        sink: Sink configuration from YAML.
        layer_name: Name of the layer ('bronze', 'silver', 'gold').
        config_class: Pydantic config class for validation.

    Returns:
        DQ report config if enabled, None otherwise.

    Raises:
        ValidationError: If sink config exists but is invalid.
    """
    sink_config = sink.get(layer_name)
    if not sink_config:
        return None

    # Check if sink_config has model_dump (is a Pydantic model)
    if not hasattr(sink_config, "model_dump"):
        return None

    validated = config_class.model_validate(sink_config.model_dump())
    if hasattr(validated, "dq_report") and validated.dq_report.enabled:
        return validated.dq_report
    return None


def _extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Extract DQ report configs from YAML.

    Args:
        yaml_config: Pipeline YAML configuration with sink settings.

    Returns:
        DQConfigsContext with bronze, silver, and gold DQ configurations.
        All values may be None if DQ reports are not configured.
    """
    from bioetl.infrastructure.schemas.dq_report_config import (
        BronzeSinkConfig,
        GoldSinkConfig,
        SilverSinkConfig,
    )

    if yaml_config is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink = getattr(yaml_config, "sink", None)
    if sink is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    bronze_config = _extract_single_dq_config(sink, "bronze", BronzeSinkConfig)
    silver_config = _extract_single_dq_config(sink, "silver", SilverSinkConfig)
    gold_config = _extract_single_dq_config(sink, "gold", GoldSinkConfig)

    return DQConfigsContext(
        bronze=bronze_config,
        silver=silver_config,
        gold=gold_config,
    )


def _get_layer_path(config: Any) -> str | None:  # Any: dynamic sink layer config
    """Extract path from layer config if available."""
    return getattr(config, "path", None) if config else None


def _has_flat_structure(config: Any) -> bool:  # Any: dynamic sink layer config
    """Check if layer config has flat_structure enabled."""
    return bool(config and getattr(config, "flat_structure", False))


def _extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract DQ report output paths and flat_structure from YAML config.

    Args:
        yaml_config: Pipeline YAML configuration with sink settings.

    Returns:
        DQOutputPathsContext with bronze_path, silver_path, gold_path, and flat_structure.
        Paths may be None if not configured.
    """
    if yaml_config is None:
        return DQOutputPathsContext(
            bronze_path=None, silver_path=None, gold_path=None, flat_structure=False
        )

    sink = getattr(yaml_config, "sink", None)
    if sink is None:
        return DQOutputPathsContext(
            bronze_path=None, silver_path=None, gold_path=None, flat_structure=False
        )

    bronze_config = sink.get("bronze")
    silver_config = sink.get("silver")
    gold_config = sink.get("gold")

    flat_structure = _has_flat_structure(silver_config) or _has_flat_structure(
        gold_config
    )

    return DQOutputPathsContext(
        bronze_path=_get_layer_path(bronze_config),
        silver_path=_get_layer_path(silver_config),
        gold_path=_get_layer_path(gold_config),
        flat_structure=flat_structure,
    )
