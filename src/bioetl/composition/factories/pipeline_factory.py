# src/bioetl/composition/factories/pipeline_factory.py
"""Consolidated Pipeline Factory module.

Provides GenericPipelineFactory and runner assembly functions for creating
fully configured pipeline instances. This module consolidates:
- GenericPipelineFactory (declarative pipeline creation)
- Runner assembly functions (PipelineRunner construction)
- Runner services factory (DI for PipelineRunner services)

Updated: Transformer injection via DI (Phase 1 refactoring).
Runner assembly delegated to internal functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.lifecycle_orchestrator import LifecycleOrchestrator
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.runner import PipelineRunner

# Re-export RunnerServices from application layer for backwards compatibility
from bioetl.application.core.runner_services import RunnerServices
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

if TYPE_CHECKING:
    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

    TPipeline = type["BasePipeline"]


TPipeline_co = TypeVar("TPipeline_co", bound="BasePipeline")


# =============================================================================
# Runner Services Factory
# =============================================================================


def build_runner_services(
    config: PipelineConfig,
    runtime: RuntimeConfig,
    services: PipelineServices,
    context: PipelineContext,
    logger: LoggerPort,
    shutdown_signal: ShutdownSignal,
    checkpoint_manager: CheckpointManager,
    lifecycle_service: MedallionLifecycleService,
) -> RunnerServices:
    """Build RunnerServices bundle.

    Factory function that creates all application services required by PipelineRunner.
    This centralizes service creation in the composition layer.

    Args:
        config: Pipeline configuration.
        runtime: Runtime configuration.
        services: Pipeline services (storage, lock, metrics, etc.).
        context: Pipeline execution context.
        logger: Structured logger.
        shutdown_signal: Shutdown signal for graceful termination.
        checkpoint_manager: Checkpoint manager.
        lifecycle_service: Medallion lifecycle service.

    Returns:
        RunnerServices bundle with all required services.
    """
    lock_manager = LockManager.create(
        lock_port=services.lock,
        run_id=context.run_id,
        provider=config.provider,
        entity_type=config.entity_type,
        run_type=runtime.run_type,
        lock_ttl=runtime.effective_lock_ttl,
        wait_for_lock=runtime.wait_for_lock,
        wait_timeout=runtime.lock_wait_timeout,
        heartbeat_interval=runtime.heartbeat_interval,
        logger=logger,
        shutdown_signal=shutdown_signal,
        checkpoint_manager=checkpoint_manager,
    )

    preflight_service = PreflightService(
        config=config,
        context=context,
        logger=logger,
        metrics=services.metrics,
    )

    postrun_service = PostrunService(
        config=config,
        runtime=runtime,
        services=services,
        logger=logger,
        lifecycle_service=lifecycle_service,
    )

    lifecycle_orchestrator = LifecycleOrchestrator(
        config=config,
        runtime=runtime,
        logger=logger,
        lifecycle_service=lifecycle_service,
    )

    return RunnerServices(
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_orch=lifecycle_orchestrator,
    )


# =============================================================================
# Runner Assembly Functions
# =============================================================================


def _create_data_source(
    create_data_source_fn: Any,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: structlog.BoundLogger,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create data source using the provided creator function.

    Args:
        create_data_source_fn: Data source creator function
        settings: Application settings
        pipeline_config: Pipeline configuration
        logger: Structured logger
        filter_config: Optional filter configuration

    Returns:
        Configured DataSourcePort
    """
    return create_data_source_fn(settings, pipeline_config, logger, filter_config)


def build_pipeline_services(
    pipeline_name: str,
    create_data_source_fn: Any,
    settings: Settings,
    logger: structlog.BoundLogger,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
) -> PipelineServices:
    """Build PipelineServices from settings.

    Args:
        pipeline_name: Name of the pipeline for config lookup
        create_data_source_fn: Data source creator function
        settings: Application settings
        logger: Structured logger
        config: Pre-loaded pipeline config (avoids duplicate I/O)
        filter_config: Optional input filter configuration
        tracer: Optional tracer (created via bootstrap_tracer())
        dq_monitor: Optional data quality monitor for anomaly detection

    Returns:
        Configured PipelineServices instance
    """
    # Import here to avoid circular imports
    from bioetl.composition.factories.services_factory import BaseServicesFactory

    pipeline_config = config or load_pipeline_config(pipeline_name)
    data_source = _create_data_source(
        create_data_source_fn, settings, pipeline_config, logger, filter_config
    )

    return BaseServicesFactory.create_common_services(
        settings=settings,
        logger=logger,
        data_source=data_source,
        pipeline_config=pipeline_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )


def create_pipeline_with_services(
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: Any,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: structlog.BoundLogger,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
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

    Returns:
        Configured pipeline instance
    """
    yaml_config = config or load_pipeline_config(pipeline_name)

    services = build_pipeline_services(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        config=yaml_config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    domain_config = yaml_config_to_domain(yaml_config)

    # Create transformer via DI if configured (with observability)
    transformer = None
    if transformer_class is not None:
        transformer = transformer_class(
            provider=provider,
            tracer=tracer,
            metrics=metrics,
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
    gold_schema: Any,
    strict_gold_validation: bool,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a pipeline instance.

    This function handles the construction of the entire pipeline execution graph,
    including record processor, executor, lifecycle service, and runner services.

    Args:
        pipeline: Configured pipeline instance
        observability: Unified observability bundle (logger, tracer, metrics, dq_monitor)
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Schema for Gold layer validation
        strict_gold_validation: Whether to enforce strict Gold validation

    Returns:
        Fully initialized PipelineRunner
    """
    # Import here to avoid circular imports
    from bioetl.composition.factories.services_factory import ServicesBuilder

    # Create Helper Components using ServicesBuilder
    checkpoint_manager = ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=observability.logger,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
    )

    record_processor = ServicesBuilder.create_record_processor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
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

    # Build runner services via DI factory (composition layer)
    runner_services = build_runner_services(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        logger=observability.logger,
        shutdown_signal=pipeline.shutdown_signal,
        checkpoint_manager=checkpoint_manager,
        lifecycle_service=lifecycle_service,
    )

    # Assemble Runner with injected RunnerServices bundle
    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=observability.logger,
        runner_services=runner_services,
        pipeline=pipeline,
        tracer=observability.tracer,
    )


# =============================================================================
# Generic Pipeline Factory
# =============================================================================


class GenericPipelineFactory(Generic[TPipeline_co]):
    """Configurable factory for creating pipelines via constructor parameters.

    Attributes:
        pipeline_name: Unique name for the pipeline
        pipeline_class: The pipeline class to instantiate
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Pandera schema for Gold layer
    """

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline_co],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: Any = None,
        data_source_creator: Any = None,
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
        self.transformer_class = transformer_class

        # Import here to avoid circular imports at module load time
        from bioetl.composition.factories.data_source_factory import DataSourceRegistry

        # Use custom creator or look up from registry
        self._create_data_source = data_source_creator or DataSourceRegistry.get(
            provider
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
    ) -> BaseTransformer | None:
        """Create transformer instance if transformer_class is configured."""
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
        """Create data source using the configured creator."""
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
        logger: structlog.BoundLogger,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metrics: MetricsPort | None = None,
    ) -> TPipeline_co:
        """Create pipeline instance with services and optional transformer."""
        return cast(
            TPipeline_co,
            create_pipeline_with_services(
                pipeline_name=self.pipeline_name,
                pipeline_class=self.pipeline_class,
                provider=self.provider,
                create_data_source_fn=self._create_data_source,
                transformer_class=self.transformer_class,
                run_id=run_id,
                runtime=runtime,
                settings=settings,
                logger=logger,
                config=config,
                filter_config=filter_config,
                tracer=tracer,
                dq_monitor=dq_monitor,
                metrics=metrics,
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
    ) -> PipelineRunner:
        """Create a fully configured PipelineRunner with all components."""
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

        # Delegate runner assembly to dedicated function
        return assemble_runner(
            pipeline=pipeline,
            observability=observability,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            strict_gold_validation=runtime.strict_gold_validation,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline_co],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: Any = None,
    transformer_class: type[BaseTransformer] | None = None,
) -> GenericPipelineFactory[TPipeline_co]:
    """Convenience function for creating pipeline factories."""
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        transformer_class=transformer_class,
    )


__all__ = [
    "GenericPipelineFactory",
    "RunnerServices",
    "assemble_runner",
    "build_pipeline_services",
    "build_runner_services",
    "create_pipeline_factory",
    "create_pipeline_with_services",
]
