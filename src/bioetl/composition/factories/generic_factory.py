"""Generic Pipeline Factory.

Provides a configurable factory that eliminates the need for boilerplate subclasses.
Pipelines can be registered declaratively using configuration rather than class inheritance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.factories.base_services_factory import BaseServicesFactory
from bioetl.composition.factories.data_source_registry import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain
from bioetl.infrastructure.validation import NoOpGoldValidator, PanderaGoldValidator

if TYPE_CHECKING:
    from uuid import UUID

    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, TracingPort
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
        gold_schema: Any | None = None,
        data_source_creator: DataSourceCreator | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            pipeline_name: Unique name for the pipeline (used for config lookup)
            pipeline_class: The pipeline class to instantiate
            provider: Provider name for data source creation
            silver_schema: Optional PyArrow schema for Silver layer
            gold_schema: Optional Pandera schema for Gold layer
            data_source_creator: Optional custom creator function. If not provided,
                uses DataSourceRegistry.get(provider)
        """
        self.pipeline_name = pipeline_name
        self.pipeline_class = pipeline_class
        self.provider = provider
        self.silver_schema = silver_schema
        self.gold_schema = gold_schema

        # Use custom creator or look up from registry
        self._create_data_source = data_source_creator or DataSourceRegistry.get(
            provider
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
    ) -> PipelineServices:
        """Build PipelineServices from settings.

        Args:
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            filter_config: Optional input filter configuration
            tracer: Optional tracer (created via bootstrap_tracer())

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
        )

    def create_with_services(
        self,
        run_id: UUID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        **kwargs: Any,
    ) -> TPipeline:
        """Create pipeline instance.

        Loads config once and reuses it for both services and pipeline.

        Args:
            run_id: Unique identifier for this pipeline run (from CLI/orchestrator)
            runtime: Pipeline runtime configuration
            settings: Application settings
            logger: Structured logger
            config: Pre-loaded pipeline config (avoids duplicate I/O)
            filter_config: Optional input filter configuration
            tracer: Optional tracer (created via bootstrap_tracer())
            **kwargs: Additional arguments for compatibility

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
        )

        domain_config = yaml_config_to_domain(yaml_config)

        return self.pipeline_class.create(
            run_id=RunID(run_id),
            runtime=runtime,
            services=services,
            config=domain_config,
        )

    def create_runner(
        self,
        run_id: UUID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: structlog.BoundLogger,
        tracer: Any,
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
            logger: Logger instance
            tracer: Tracer instance
            filter_config: Optional filter configuration
            config: Pre-loaded pipeline config (optional)

        Returns:
            Fully initialized PipelineRunner
        """
        # Load config once if not provided
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        # Create pipeline instance with services and tracer
        pipeline = self.create_with_services(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=logger,
            config=yaml_config,
            filter_config=filter_config,
            tracer=tracer,
        )

        # Create Helper Components
        checkpoint_manager = self._create_checkpoint_manager(
            pipeline=pipeline,
            logger=logger,
            run_id=run_id,
            resume=runtime.resume,
        )

        record_processor = self._create_record_processor(pipeline)

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

        # Assemble Runner
        return PipelineRunner(
            config=pipeline.config,
            runtime=pipeline.runtime,
            services=pipeline.services,
            context=pipeline.context,
            executor=executor,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=pipeline.shutdown_signal,
            logger=logger,
            pipeline=pipeline,
            tracer=tracer,
        )

    def _create_checkpoint_manager(
        self,
        pipeline: TPipeline,
        logger: structlog.BoundLogger,
        run_id: UUID,
        resume: bool,
    ) -> CheckpointManager:
        """Create configured CheckpointManager."""
        from bioetl.domain.types import RunID

        return CheckpointManager(
            checkpoint_port=pipeline.services.checkpoint,
            logger=logger,
            pipeline_name=pipeline.config.pipeline_name,
            run_id=RunID(run_id),
            resume=resume,
        )

    def _create_record_processor(self, pipeline: TPipeline) -> RecordProcessor:
        """Create configured RecordProcessor."""
        error_classifier = ErrorClassifier()
        table_config = TableConfig(
            primary_keys=pipeline.config.primary_keys,
            silver_table=pipeline.config.silver_table,
            gold_table=pipeline.config.gold_table,
            silver_write_mode=pipeline.config.write_mode,
            gold_write_mode=pipeline.config.gold_write_mode,
        )

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            dq_config=pipeline.config.dq,
            table_config=table_config,
        )

        # Create Gold validator from schema (DI pattern)
        gold_validator = (
            PanderaGoldValidator(self.gold_schema)
            if self.gold_schema
            else NoOpGoldValidator()
        )

        return RecordProcessor(
            services=pipeline.services,
            error_classifier=error_classifier,
            context=pipeline.context,
            config=processor_config,
            transform_callback=pipeline.transform_bronze_to_silver,
            gold_filter_callback=pipeline.should_write_gold,
            gold_transform_callback=pipeline.transform_for_gold,
            gold_validator=gold_validator,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: Any | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Convenience function for creating pipeline factories.

    Args:
        pipeline_name: Unique pipeline name
        pipeline_class: Pipeline class to instantiate
        provider: Data source provider name
        silver_schema: Optional Silver layer schema
        gold_schema: Optional Gold layer schema

    Returns:
        Configured GenericPipelineFactory

    Example:
        >>> factory = create_pipeline_factory(
        ...     pipeline_name="chembl_activity",
        ...     pipeline_class=ChEMBLActivityPipeline,
        ...     provider="chembl",
        ...     silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        ... )
    """
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
    )
