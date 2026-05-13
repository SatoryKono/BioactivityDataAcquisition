"""Pipeline service builder helper functions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.wiring.runtime import (
    BatchProcessingComponents,
    CheckpointRuntimeService,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services._pipeline_batch_executor_types import (
    BatchExecutorBuildRequest,
    BatchProcessingComponentsFactory,
)
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
        TransformCallback,
    )
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.application.services.checkpoint_compatibility_service import (
        CheckpointCompatibilityService,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.medallion import LoadingStrategy
    from bioetl.domain.ports import (
        CheckpointPort,
        GoldValidatorPort,
        LoggerPort,
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
    domain_event_emitter: DomainEventEmitterProtocol | None = None,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
) -> BatchProcessingComponents:
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
    checkpoint_compatibility_service: CheckpointCompatibilityService | None = None,
    current_metadata: CheckpointMetadata | None = None,
    compatibility_policy: Literal[
        "observe", "soft_fail", "hard_fail"
    ] = "soft_fail",
) -> CheckpointRuntimeService:
    return CheckpointRuntimeService(
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
    request: BatchExecutorBuildRequest,
) -> BatchExecutor:
    return build_batch_executor_from_pipeline(request)


__all__ = [
    "BatchExecutorBuildRequest",
    "BatchProcessingComponents",
    "BatchProcessingComponentsFactory",
    "create_batch_executor_from_pipeline",
    "create_batch_processing_components",
    "create_checkpoint_manager",
    "create_record_processor_from_pipeline",
]
