"""Runner assembly module for pipeline factories.

Provides functions for building PipelineRunner and its services.
Extracted from GenericPipelineFactory to reduce file size and improve cohesion.

This module handles the "assembly" phase of pipeline creation:
- Building PipelineServices from settings
- Creating fully configured PipelineRunner instances
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.factories.base_services_factory import BaseServicesFactory
from bioetl.composition.factories.runner_services import build_runner_services
from bioetl.composition.factories.services_builder import ServicesBuilder
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

if TYPE_CHECKING:
    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.composition.factories.data_source_registry import DataSourceCreator
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

    TPipeline = type["BasePipeline"]


def create_data_source(
    create_data_source_fn: DataSourceCreator,
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
    create_data_source_fn: DataSourceCreator,
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
    pipeline_config = config or load_pipeline_config(pipeline_name)
    data_source = create_data_source(
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
    create_data_source_fn: DataSourceCreator,
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
        tracer=observability.tracer,
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
