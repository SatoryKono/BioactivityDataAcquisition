"""Generic Pipeline Factory.

Provides a configurable factory that eliminates the need for boilerplate subclasses.
Pipelines can be registered declaratively using configuration rather than class inheritance.

Updated: Transformer injection via DI (Phase 1 refactoring).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.factories.base_services_factory import BaseServicesFactory
from bioetl.composition.factories.data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.composition.factories.services_builder import ServicesBuilder
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

if TYPE_CHECKING:
    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")


class GenericPipelineFactory(Generic[TPipeline]):
    """Configurable factory for creating pipelines.

    Unlike BasePipelineFactory which requires subclassing, GenericPipelineFactory
    is configured via constructor parameters. This reduces boilerplate and
    centralizes pipeline definitions.

    Example:
        >>> from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
        >>> from bioetl.infrastructure.schemas.silver import CHEMBL_ACTIVITY_SCHEMA
        >>>
        >>> factory = GenericPipelineFactory(
        ...     pipeline_name="chembl_activity",
        ...     pipeline_class=ChEMBLActivityPipeline,
        ...     provider="chembl",
        ...     silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        ... )
        >>>
        >>> # Create pipeline
        >>> pipeline = factory.create_with_services(runtime, settings, logger)

    Attributes:
        pipeline_name: Unique name for the pipeline
        pipeline_class: The pipeline class to instantiate
        silver_schema: PyArrow schema for Silver layer
    """

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: Any = None,
        data_source_creator: DataSourceCreator | None = None,
        transformer_class: type[BaseTransformer] | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            pipeline_name: Unique name for the pipeline (used for config lookup)
            pipeline_class: The pipeline class to instantiate
            provider: Provider name for data source creation
            silver_schema: Optional PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer validation (required)
            data_source_creator: Optional custom creator function. If not provided,
                uses DataSourceRegistry.get(provider)
            transformer_class: Transformer class for Bronze→Silver transformation.
                If provided, factory will create and inject transformer into pipeline.
                This is the preferred DI approach.

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
        self.transformer_class = transformer_class

        # Use custom creator or look up from registry
        self._create_data_source = data_source_creator or DataSourceRegistry.get(
            provider
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
    ) -> BaseTransformer | None:
        """Create transformer instance if transformer_class is configured.

        Args:
            tracer: Optional tracer for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).

        Returns:
            Transformer instance or None if no transformer_class configured.
        """
        if self.transformer_class is None:
            return None
        return self.transformer_class(
            provider=self.provider,
            tracer=tracer,
            metrics=metrics,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: structlog.BoundLogger,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create data source using the configured creator.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration
            logger: LoggerPort instance for structured logging
            filter_config: Optional filter configuration

        Returns:
            Configured DataSourcePort
        """
        return self._create_data_source(
            settings, pipeline_config, logger, filter_config
        )

    def build_services(
        self,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineServices:
        """Build PipelineServices from settings.

        Args:
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            filter_config: Optional input filter configuration
            tracer: Optional tracer (created via bootstrap_tracer())
            dq_monitor: Optional data quality monitor for anomaly detection

        Returns:
            Configured PipelineServices instance
        """
        pipeline_config = config or load_pipeline_config(self.pipeline_name)
        data_source = self.create_data_source(
            settings, pipeline_config, logger, filter_config
        )

        return BaseServicesFactory.create_common_services(
            settings=settings,
            logger=logger,
            data_source=data_source,
            pipeline_config=pipeline_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
        )

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metrics: MetricsPort | None = None,
    ) -> TPipeline:
        """Create pipeline instance.

        Loads config once and reuses it for both services and pipeline.
        If transformer_class is configured, creates and injects transformer via DI.

        Args:
            run_id: Unique identifier for this pipeline run (from CLI/orchestrator)
            runtime: Pipeline runtime configuration
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            filter_config: Optional input filter configuration
            tracer: Optional tracer (created via bootstrap_tracer())
            dq_monitor: Optional data quality monitor for anomaly detection
            metrics: Optional metrics port for transformer observability (O1)

        Returns:
            Configured pipeline instance
        """
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        services = self.build_services(
            settings=settings,
            logger=logger,
            config=yaml_config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
        )

        domain_config = yaml_config_to_domain(yaml_config)

        # Create transformer via DI if configured (with observability O1)
        transformer = self.create_transformer(
            tracer=tracer,
            metrics=metrics,
        )

        return self.pipeline_class.create(
            run_id=run_id,
            runtime=runtime,
            services=services,
            config=domain_config,
            transformer=transformer,
        )

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
    ) -> PipelineRunner:
        """Create a fully configured PipelineRunner.

        Encapsulates the construction of the entire pipeline execution graph,
        including services, pipeline instance, record processor, and executor.

        Args:
            run_id: Unique identifier for this run
            runtime: Runtime configuration
            settings: Application settings
            observability: Unified observability bundle (logger, tracer, metrics, dq_monitor)
            filter_config: Optional filter configuration
            config: Pre-loaded pipeline config (optional)

        Returns:
            Fully initialized PipelineRunner
        """
        # Load config once if not provided
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        # Create pipeline instance with services, tracer, metrics, and dq_monitor (O1)
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
        )

        # Create Helper Components using ServicesBuilder
        checkpoint_manager = ServicesBuilder.create_checkpoint_manager(
            checkpoint_port=pipeline.services.checkpoint,
            logger=observability.logger,
            pipeline_name=pipeline.config.pipeline_name,
            run_id=run_id,
            resume=runtime.resume,
        )

        record_processor = ServicesBuilder.create_record_processor_from_pipeline(
            pipeline=pipeline,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
        )

        # Create Executor
        executor = PipelineExecutor(
            services=pipeline.services,
            record_processor=record_processor,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=pipeline.shutdown_signal,
            entity_type=pipeline.config.entity_type,
            batch_size=pipeline.config.batch_size,
            checkpoint_interval=pipeline.config.checkpoint_interval,
        )

        # Create lifecycle service (M5)
        lifecycle_service = MedallionLifecycleService(
            storage=pipeline.services.storage,
            logger=observability.logger,
        )

        # Assemble Runner
        return PipelineRunner(
            config=pipeline.config,
            runtime=pipeline.runtime,
            services=pipeline.services,
            context=pipeline.context,
            executor=executor,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=pipeline.shutdown_signal,
            logger=observability.logger,
            pipeline=pipeline,
            tracer=observability.tracer,
            lifecycle_service=lifecycle_service,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: Any = None,
    transformer_class: type[BaseTransformer] | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Convenience function for creating pipeline factories.

    Args:
        pipeline_name: Unique pipeline name
        pipeline_class: Pipeline class to instantiate
        provider: Data source provider name
        silver_schema: Optional Silver layer schema
        gold_schema: Pandera schema for Gold layer validation (required)
        transformer_class: Transformer class for Bronze→Silver transformation (DI)

    Returns:
        Configured GenericPipelineFactory

    Example:
        >>> factory = create_pipeline_factory(
        ...     pipeline_name="chembl_activity",
        ...     pipeline_class=ChEMBLActivityPipeline,
        ...     provider="chembl",
        ...     silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        ...     transformer_class=ActivityTransformer,
        ... )
    """
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        transformer_class=transformer_class,
    )
