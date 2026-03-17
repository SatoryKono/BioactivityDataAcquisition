"""Pipeline-bound helper builders for ServicesBuilder."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.core.batch_execution_state_service import (
    BatchExecutionStateService,
)
from bioetl.application.core.batch_executor import (
    BatchExecutor,
    BatchExecutorDependencies,
)
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer import BatchTransformer
from bioetl.application.core.batch_writer import BatchWriter, BatchWriterOptions
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointManagerService,
)
from bioetl.application.core.protocols import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
)
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services.pipeline_processing import (
    build_components_and_processing_service,
)
from bioetl.composition.factories.services.runtime_managers import (
    build_runtime_managers,
)
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.record_processor import RecordProcessor
    from bioetl.domain.config import DQConfig, MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.medallion import LoadingStrategy
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        CheckpointPort,
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        TracingPort,
    )
    from bioetl.domain.types import GoldSchemaType, RunID


@dataclass(frozen=True, slots=True)
class BatchProcessingComponents:
    """Injected components shared by RecordProcessor and BatchExecutor."""

    batch_metrics: BatchMetricsRecorderService
    transformer: BatchTransformer
    writer: BatchWriter


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
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
) -> BatchProcessingComponents:
    """Create batch metrics/transformer/writer stack via composition DI."""
    batch_metrics = BatchMetricsRecorderService(
        services.metrics,
        f"{config.provider}_{config.entity_type}",
        context.run_type.value,
    )
    quarantine_manager = QuarantineManagerService(
        quarantine_port=services.quarantine,
        pipeline_name=config.pipeline_name,
        metrics=services.metrics,
    )
    transformer = BatchTransformer(
        context=context,
        config=config,
        error_classifier=error_classifier,
        quarantine_manager=quarantine_manager,
        batch_metrics=batch_metrics,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
    )
    column_orderer = (
        ColumnOrderer(context.logger, column_groups=config.column_groups)
        if config.column_groups
        else None
    )
    writer = BatchWriter(
        storage=services.storage,
        context=context,
        config=config,
        gold_validator=gold_validator,
        error_classifier=error_classifier,
        batch_metrics=batch_metrics,
        options=BatchWriterOptions(
            tracer=tracer,
            lock_validator=lock_validator,
            column_orderer=column_orderer,
        ),
    )
    return BatchProcessingComponents(
        batch_metrics=batch_metrics, transformer=transformer, writer=writer
    )


def create_checkpoint_manager(
    checkpoint_port: CheckpointPort,
    logger: LoggerPort,
    pipeline_name: str,
    run_id: RunID,
    resume: bool,
    *,
    loading_strategy: LoadingStrategy | None = None,
) -> CheckpointManagerService:
    """Create configured CheckpointManagerService."""
    return CheckpointManagerService(
        checkpoint_port=checkpoint_port,
        logger=logger,
        pipeline_name=pipeline_name,
        run_id=run_id,
        resume=resume,
        loading_strategy=loading_strategy,
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
    return create_record_processor_fn(
        services=pipeline.services,
        context=pipeline.context,
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=pipeline.config.dq,
        primary_keys=pipeline.config.table.primary_keys,
        silver_table=pipeline.config.effective_silver_table,
        gold_table=pipeline.config.effective_gold_table,
        silver_write_mode=pipeline.config.table.silver_write_mode,
        gold_write_mode=pipeline.config.table.gold_write_mode,
        on_schema_mismatch=pipeline.config.table.on_schema_mismatch,
        transform_callback=callbacks.transform,
        gold_filter_callback=callbacks.gold_filter,
        gold_transform_callback=callbacks.gold_transform,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
        column_groups=tuple(pipeline.config.column_groups),
        scd_config=pipeline.config.scd_config,
    )


def _build_record_processor_config(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    bronze_output_path: str | None,
    silver_output_path: str | None,
    gold_output_path: str | None,
    flat_structure: bool,
) -> tuple[RecordProcessorConfig, PanderaGoldValidator]:
    processor_config = RecordProcessorConfig(
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=cast("DQConfig | None", pipeline.config.dq),
        table_config=pipeline.config.table,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        column_groups=pipeline.config.column_groups,
        scd_config=pipeline.config.scd_config,
    )
    gold_validator = PanderaGoldValidator(
        cast("pa.DataFrameSchema | None", gold_schema), strict=strict_gold_validation
    )
    return processor_config, gold_validator


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
) -> BatchExecutor:
    """Create BatchExecutor from pipeline using delegated component factories."""
    gold_filter = (
        cast(GoldFilterCallback, lambda _context, _record: False)
        if pipeline.runtime.skip_gold
        else callbacks.gold_filter
    )
    processor_config, gold_validator = _build_record_processor_config(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
    )
    (
        memory_manager,
        tracing_manager,
        effective_batch_id_factory,
        progress_service,
        checkpoint_recovery_service,
        execution_run_service,
    ) = build_runtime_managers(
        pipeline=pipeline,
        processor_config=processor_config,
        checkpoint_manager=checkpoint_manager,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        tracer=tracer,
        batch_id_factory=batch_id_factory,
    )
    components, batch_processing_service = build_components_and_processing_service(
        pipeline=pipeline,
        processor_config=processor_config,
        error_classifier=ErrorClassifier(),
        callbacks=callbacks,
        gold_filter=gold_filter,
        gold_validator=gold_validator,
        tracer=tracer,
        lock_validator=lock_validator,
        tracing_manager=tracing_manager,
        batch_id_factory=effective_batch_id_factory,
        create_batch_processing_components_fn=create_batch_processing_components_fn,
    )
    execution_state_service = BatchExecutionStateService(
        batch_processing_service=batch_processing_service
    )
    extraction_loop_service = BatchExtractionLoopService(
        batch_processing_service=batch_processing_service,
        shutdown_signal=shutdown_signal,
        memory_manager=memory_manager,
        progress_service=progress_service,
        checkpoint_recovery_service=checkpoint_recovery_service,
        checkpoint_interval=pipeline.config.checkpoint_interval
        or BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL,
    )
    deps = BatchExecutorDependencies(
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        memory_manager=memory_manager,
        execution_run_service=execution_run_service,
        extraction_loop_service=extraction_loop_service,
        execution_state_service=execution_state_service,
    )
    return BatchExecutor(
        services=pipeline.services,
        context=pipeline.context,
        config=processor_config,
        dependencies=deps,
        batch_size=pipeline.config.batch_size,
        checkpoint_interval=pipeline.config.checkpoint_interval,
    )


__all__ = [
    "BatchProcessingComponents",
    "create_batch_executor_from_pipeline",
    "create_batch_processing_components",
    "create_checkpoint_manager",
    "create_record_processor_from_pipeline",
]
