"""Pipeline-bound facade helpers for ServicesBuilder."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal
from bioetl.application.core.wiring.runtime import (
    BatchProcessingComponents,
    CheckpointManagerService,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services.pipeline_batch_executor_builder import (
    create_batch_executor_from_pipeline as build_batch_executor_from_pipeline,
)
from bioetl.composition.factories.services.pipeline_processing_components_builder import (
    create_batch_processing_components as build_batch_processing_components,
)
from bioetl.composition.factories.services.pipeline_record_processor_builder import (
    create_record_processor_from_pipeline as build_record_processor_from_pipeline,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import (
        BasePipeline,
        BatchExecutor,
        GoldFilterCallback,
        GoldTransformCallback,
        PipelineService,
        RecordProcessor,
        RecordProcessorConfig,
        ShutdownSignal,
        TransformCallback,
    )
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterPort,
    )
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.medallion import LoadingStrategy
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        CheckpointPort,
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import GoldSchemaType, RunID
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def create_batch_processing_components(
    *,
    services: PipelineService,
    context: PipelineContext,
    config: RecordProcessorConfig,
    error_classifier: ErrorClassifier,
    transform_callback: TransformCallback,
    gold_filter_callback: GoldFilterCallback,
    gold_transform_callback: GoldTransformCallback,
    gold_validator: GoldValidatorPort,
    tracer: TracingPort | None = None,
    domain_event_emitter: DomainEventEmitter | None = None,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
) -> BatchProcessingComponents:
    """Create batch metrics/transformer/writer stack via composition DI."""
    return build_batch_processing_components(
        services=services,
        context=context,
        config=config,
        error_classifier=error_classifier,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator,
        tracer=tracer,
        domain_event_emitter=domain_event_emitter,
        lock_validator=lock_validator,
    )

def create_checkpoint_manager(
    checkpoint_port: CheckpointPort,
    logger: LoggerPort,
    pipeline_name: str,
    run_id: RunID,
    resume: bool,
    *,
    loading_strategy: LoadingStrategy | None = None,
    metrics: MetricsPort | None = None,
    checkpoint_compatibility_service: object | None = None,
    current_metadata: CheckpointMetadata | None = None,
    compatibility_policy: Literal["observe", "soft_fail", "hard_fail"] = "soft_fail",
) -> CheckpointManagerService:
    """Create configured CheckpointManagerService."""
    return CheckpointManagerService(
        checkpoint_port=checkpoint_port,
        logger=logger,
        pipeline_name=pipeline_name,
        run_id=run_id,
        resume=resume,
        loading_strategy=loading_strategy,
        metrics=metrics,
        checkpoint_compatibility_service=checkpoint_compatibility_service,
        current_metadata=current_metadata,
        compatibility_policy=compatibility_policy,
    )

def create_record_processor_from_pipeline(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    callbacks: PipelineCallbacksContext,
    create_record_processor_fn: Callable[..., RecordProcessor],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
) -> RecordProcessor:
    """Create RecordProcessor from pipeline using delegated builder."""
    return build_record_processor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        callbacks=callbacks,
        create_record_processor_fn=create_record_processor_fn,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
    )

def create_batch_executor_from_pipeline(
    *,
    pipeline: BasePipeline,
    callbacks: PipelineCallbacksContext,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    checkpoint_manager: CheckpointManagerService,
    shutdown_signal: ShutdownSignal,
    create_batch_processing_components_fn: Callable[..., BatchProcessingComponents],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
    memory_monitor: MemoryMonitorPort | None = None,
    memory_config: MemoryConfig | None = None,
    bronze_output_path: str | None = None,
    silver_output_path: str | None = None,
    gold_output_path: str | None = None,
    flat_structure: bool = False,
    batch_id_factory: BatchIdGeneratorPort | None = None,
    domain_event_emitter: DomainEventEmitter | None = None,
) -> BatchExecutor:
    """Create BatchExecutor from pipeline using delegated component factories."""
    return build_batch_executor_from_pipeline(
        pipeline=pipeline,
        callbacks=callbacks,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=shutdown_signal,
        create_batch_processing_components_fn=create_batch_processing_components_fn,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        batch_id_factory=batch_id_factory,
        domain_event_emitter=domain_event_emitter,
    )
__all__ = ["BatchProcessingComponents", "create_batch_executor_from_pipeline", "create_batch_processing_components", "create_checkpoint_manager", "create_record_processor_from_pipeline"]
