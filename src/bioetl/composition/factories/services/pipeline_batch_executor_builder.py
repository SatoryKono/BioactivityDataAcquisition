"""Batch-executor assembly helpers for pipeline builder facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import (
    BatchExecutionFSM,
    BatchExecutionStateService,
    BatchExecutor,
    BatchExecutorDependencies,
    BatchExtractionLoopService,
    GoldFilterCallback,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services._pipeline_batch_executor_types import (
    BatchExecutorBuildRequest,
)
from bioetl.composition.factories.services.pipeline_processing import (
    build_components_and_processing_service,
)
from bioetl.composition.factories.services.pipeline_record_processor_builder import (
    build_record_processor_config_and_validator,
)
from bioetl.composition.factories.services.runtime_managers import (
    build_runtime_managers,
)
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    from bioetl.application.core.wiring.runtime import (
        BasePipeline,
        BatchCheckpointRecoveryService,
        BatchExecutionRunService,
        BatchMemoryManagerService,
        BatchProcessingService,
        BatchProgressService,
        ShutdownSignal,
    )


def create_batch_executor_from_pipeline(
    request: BatchExecutorBuildRequest,
) -> BatchExecutor:
    """Create BatchExecutor from pipeline using delegated component factories."""
    gold_filter = _resolve_gold_filter(
        pipeline=request.pipeline,
        callbacks=request.callbacks,
    )
    processor_config, gold_validator = build_record_processor_config_and_validator(
        pipeline=request.pipeline,
        silver_schema=request.silver_schema,
        gold_schema=request.gold_schema,
        strict_gold_validation=request.strict_gold_validation,
        bronze_output_path=request.bronze_output_path,
        silver_output_path=request.silver_output_path,
        gold_output_path=request.gold_output_path,
        flat_structure=request.flat_structure,
        gold_validator_factory=PanderaGoldValidator,
    )
    runtime_managers = build_runtime_managers(
        pipeline=request.pipeline,
        processor_config=processor_config,
        checkpoint_manager=request.checkpoint_manager,
        memory_monitor=request.memory_monitor,
        memory_config=request.memory_config,
        tracer=request.tracer,
        batch_id_factory=request.batch_id_factory,
    )
    (
        memory_manager,
        tracing_manager,
        effective_batch_id_factory,
        progress_service,
        checkpoint_recovery_service,
        execution_run_service,
    ) = runtime_managers
    _, batch_processing_service = build_components_and_processing_service(
        pipeline=request.pipeline,
        processor_config=processor_config,
        error_classifier=ErrorClassifier(),
        callbacks=request.callbacks,
        gold_filter=gold_filter,
        gold_validator=gold_validator,
        tracer=request.tracer,
        domain_event_emitter=request.domain_event_emitter,
        lock_validator=request.lock_validator,
        tracing_manager=tracing_manager,
        batch_id_factory=effective_batch_id_factory,
        create_batch_processing_components_fn=(
            request.create_batch_processing_components_fn
        ),
    )
    deps = _build_batch_executor_dependencies(
        pipeline=request.pipeline,
        shutdown_signal=request.shutdown_signal,
        memory_manager=memory_manager,
        progress_service=progress_service,
        checkpoint_recovery_service=checkpoint_recovery_service,
        execution_run_service=execution_run_service,
        batch_processing_service=batch_processing_service,
    )
    return BatchExecutor(
        services=request.pipeline.services,
        context=request.pipeline.context,
        config=processor_config,
        dependencies=deps,
        batch_size=request.pipeline.config.batch_size,
        checkpoint_interval=request.pipeline.config.checkpoint_interval,
    )


def _resolve_gold_filter(
    *,
    pipeline: BasePipeline,
    callbacks: PipelineCallbacksContext,
) -> GoldFilterCallback:
    """Resolve the effective gold filter based on runtime skip configuration."""
    if pipeline.runtime.skip_gold:
        return cast(GoldFilterCallback, lambda _context, _record: False)
    return callbacks.gold_filter


def _build_batch_executor_dependencies(
    *,
    pipeline: BasePipeline,
    shutdown_signal: ShutdownSignal,
    memory_manager: BatchMemoryManagerService,
    progress_service: BatchProgressService,
    checkpoint_recovery_service: BatchCheckpointRecoveryService,
    execution_run_service: BatchExecutionRunService,
    batch_processing_service: BatchProcessingService,
) -> BatchExecutorDependencies:
    """Create the runtime dependency bundle for BatchExecutor."""
    execution_state_service = BatchExecutionStateService()
    extraction_loop_service = BatchExtractionLoopService(
        batch_processing_service=batch_processing_service,
        shutdown_signal=shutdown_signal,
        memory_manager=memory_manager,
        progress_service=progress_service,
        checkpoint_recovery_service=checkpoint_recovery_service,
        checkpoint_interval=pipeline.config.checkpoint_interval
        or BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL,
    )
    return BatchExecutorDependencies(
        memory_manager=memory_manager,
        execution_run_service=execution_run_service,
        extraction_loop_service=extraction_loop_service,
        execution_state_service=execution_state_service,
        processing_port=batch_processing_service,
        fsm=BatchExecutionFSM(),
    )


__all__ = ["create_batch_executor_from_pipeline"]
