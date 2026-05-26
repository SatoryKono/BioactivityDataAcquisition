"""High-level service builder facade helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.wiring.runtime import (
    BatchExecutor,
    BatchProcessingComponents,
    CheckpointRuntimeService,
    GoldFilterCallback,
    GoldTransformCallback,
    PipelineService,
    RecordProcessor,
    RecordProcessorConfig,
    TransformCallback,
)
from bioetl.composition.factories.services._builder_record_processor_support import (
    _RecordProcessorBuildRequest,
    create_record_processor_impl,
)
from bioetl.composition.factories.services.callbacks import (
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.services.pipeline_builder import (
    BatchExecutorBuildRequest,
    create_batch_executor_from_pipeline,
    create_batch_processing_components,
    create_checkpoint_manager,
    create_record_processor_from_pipeline,
)
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.medallion import LoadingStrategy

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import BasePipeline
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.application.services.checkpoint_compatibility_service import (
        CheckpointCompatibilityService,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        CheckpointPort,
        ClockPort,
        GoldValidatorPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import (
        GoldSchemaType,
        RunID,
    )
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
__all__ = [
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


class ServicesBuilder:
    @staticmethod
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
        return create_batch_processing_components(
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

    @staticmethod
    def create_checkpoint_manager(
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
        *,
        loading_strategy: LoadingStrategy | None = None,
        metrics: MetricsPort | None = None,
        clock: ClockPort | None = None,
        checkpoint_compatibility_service: CheckpointCompatibilityService | None = None,
        current_metadata: CheckpointMetadata | None = None,
        compatibility_policy: Literal[
            "observe", "soft_fail", "hard_fail"
        ] = "soft_fail",
    ) -> CheckpointRuntimeService:
        return create_checkpoint_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
            loading_strategy=loading_strategy,
            metrics=metrics,
            clock=clock,
            checkpoint_compatibility_service=checkpoint_compatibility_service,
            current_metadata=current_metadata,
            compatibility_policy=compatibility_policy,
        )

    @staticmethod
    def create_record_processor(
        *,
        request: _RecordProcessorBuildRequest,
    ) -> RecordProcessor:
        return create_record_processor_impl(request=request)

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: GoldSchemaType,
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> RecordProcessor:
        callbacks = extract_pipeline_callbacks(pipeline)
        return create_record_processor_from_pipeline(
            pipeline=pipeline,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            callbacks=callbacks,
            create_record_processor_fn=ServicesBuilder.create_record_processor,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            tracer=pipeline.services.tracing,
        )

    @staticmethod
    def create_batch_executor_from_pipeline(
        request: BatchExecutorBuildRequest,
    ) -> BatchExecutor:
        callbacks = extract_pipeline_callbacks(request.pipeline)
        return create_batch_executor_from_pipeline(
            BatchExecutorBuildRequest(
                pipeline=request.pipeline,
                callbacks=callbacks,
                silver_schema=request.silver_schema,
                gold_schema=request.gold_schema,
                checkpoint_manager=request.checkpoint_manager,
                shutdown_signal=request.shutdown_signal,
                create_batch_processing_components_fn=(
                    ServicesBuilder.create_batch_processing_components
                ),
                strict_gold_validation=request.strict_gold_validation,
                lock_validator=request.lock_validator,
                tracer=request.tracer,
                memory_monitor=request.memory_monitor,
                memory_config=request.memory_config,
                bronze_output_path=request.bronze_output_path,
                silver_output_path=request.silver_output_path,
                gold_output_path=request.gold_output_path,
                flat_structure=request.flat_structure,
                batch_id_factory=request.batch_id_factory,
                domain_event_emitter=request.domain_event_emitter,
            )
        )
