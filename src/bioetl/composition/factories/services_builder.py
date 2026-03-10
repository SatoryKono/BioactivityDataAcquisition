"""Builder for pipeline infrastructure components."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Literal, cast

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.checkpoint_manager import CheckpointManagerService
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.protocols import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
)
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services_factory_pipeline_builder import (
    BatchProcessingComponents,
    create_batch_executor_from_pipeline,
    create_batch_processing_components,
    create_checkpoint_manager,
    create_record_processor_from_pipeline,
)
from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pandera
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.domain.config import DQConfig, MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        CheckpointPort,
        DataNormalizationPort,
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        TracingPort,
    )
    from bioetl.domain.services import DataNormalizationConfig
    from bioetl.domain.types import RunID

__all__ = [
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


def extract_pipeline_callbacks(pipeline: BasePipeline) -> PipelineCallbacksContext:
    """Extract transformation callbacks from transformer or legacy methods.

    Args:
        pipeline: Pipeline instance from which to extract transform callbacks.

    Returns:
        PipelineCallbacksContext with transform, gold filter, and gold transform callbacks.
    """
    transformer = pipeline.transformer
    if transformer is not None:
        return PipelineCallbacksContext(
            transform=cast(TransformCallback, transformer.transform),
            gold_filter=cast(GoldFilterCallback, transformer.should_write_gold),
            gold_transform=cast(GoldTransformCallback, transformer.transform_for_gold),
        )

    # Fallback for pipelines without explicit transformer (legacy)
    return PipelineCallbacksContext(
        transform=cast(TransformCallback, pipeline.transform_bronze_to_silver),
        gold_filter=cast(
            GoldFilterCallback,
            getattr(pipeline, "should_write_gold", lambda _context, record: True),
        ),
        gold_transform=cast(
            GoldTransformCallback,
            getattr(
                pipeline,
                "transform_for_gold",
                lambda _context, silver_record: silver_record,
            ),
        ),
    )


class ServicesBuilder:
    """Builder for pipeline infrastructure components."""

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
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> BatchProcessingComponents:
        """Create batch metrics/transformer/writer stack via composition DI."""
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
    ) -> CheckpointManagerService:
        """Create configured CheckpointManagerService.

        Args:
            checkpoint_port: CheckpointPort for reading and writing checkpoint state.
            logger: LoggerPort for structured checkpoint event logging.
            pipeline_name: Pipeline identifier used for checkpoint scoping.
            run_id: Unique run identifier embedded in checkpoint records.
            resume: If True, resumes from existing checkpoint instead of starting fresh.
            loading_strategy: Optional strategy controlling checkpoint loading behavior.

        Returns:
            CheckpointManagerService configured for the pipeline run.
        """
        return create_checkpoint_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
            loading_strategy=loading_strategy,
        )

    @staticmethod
    def create_record_processor(
        services: PipelineService,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        silver_schema: pa.Schema | None,
        gold_schema: type[pandera.DataFrameModel],
        dq_config: DQConfig | None,
        primary_keys: Sequence[str],
        silver_table: str,
        gold_table: str | None,
        silver_write_mode: SilverWriteMode,
        gold_write_mode: GoldWriteMode,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        tracer: TracingPort | None = None,
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        column_groups: tuple[ColumnGroupConfig, ...] = (),
        scd_config: dict[str, str] | None = None,
    ) -> RecordProcessor:
        """Create configured ``RecordProcessor`` for pipeline execution."""
        effective_tracer = tracer or services.tracing
        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=dq_config,
            table_config=TableConfig(
                primary_keys=tuple(primary_keys),
                silver_table=silver_table,
                gold_table=gold_table,
                silver_write_mode=silver_write_mode,
                gold_write_mode=gold_write_mode,
                on_schema_mismatch=on_schema_mismatch,
            ),
            column_groups=column_groups,
            scd_config=scd_config,
        )

        components = ServicesBuilder.create_batch_processing_components(
            services=services,
            context=context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=PanderaGoldValidator(
                cast("pa.DataFrameSchema | None", gold_schema),
                strict=strict_gold_validation,
            ),
            tracer=effective_tracer,
            lock_validator=lock_validator,
        )

        return RecordProcessor(
            context=context,
            batch_metrics=components.batch_metrics,
            transformer=components.transformer,
            writer=components.writer,
            config=processor_config,
            tracer=effective_tracer,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: type[pandera.DataFrameModel],
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> RecordProcessor:
        """Create RecordProcessor from pipeline instance.

        Args:
            pipeline: Configured pipeline instance providing services, context, and callbacks.
            silver_schema: Optional PyArrow schema for Silver layer validation.
            gold_schema: Pandera DataFrameModel class for Gold layer validation.
            strict_gold_validation: If True, raises on Gold schema violations. Defaults to True.
            lock_validator: Optional async callable for lock validation before writes.

        Returns:
            RecordProcessor configured from the pipeline's services and context.
        """
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
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: type[pandera.DataFrameModel],
        checkpoint_manager: CheckpointManagerService,
        shutdown_signal: ShutdownSignal,
        *,
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
        """Create BatchExecutor from pipeline instance.

        Args:
            pipeline: Configured pipeline instance providing services, context, and callbacks.
            silver_schema: Optional PyArrow schema for Silver layer validation.
            gold_schema: Pandera DataFrameModel class for Gold layer validation.
            checkpoint_manager: CheckpointManagerService for batch-level checkpointing.
            shutdown_signal: Signal used to gracefully terminate batch execution.
            strict_gold_validation: If True, raises on Gold schema violations. Defaults to True.
            lock_validator: Optional async callable for lock validation before writes.
            tracer: Optional TracingPort for distributed tracing.
            memory_monitor: Optional monitor for memory pressure tracking.
            memory_config: Optional memory configuration for batch sizing.
            bronze_output_path: Optional path override for Bronze output.
            silver_output_path: Optional path override for Silver output.
            gold_output_path: Optional path override for Gold output.
            flat_structure: If True, writes use flat directory structure. Defaults to False.
            batch_id_factory: Optional custom batch ID generator.

        Returns:
            BatchExecutor configured from the pipeline's services, context, and config.
        """
        callbacks = extract_pipeline_callbacks(pipeline)
        return create_batch_executor_from_pipeline(
            pipeline=pipeline,
            callbacks=callbacks,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=shutdown_signal,
            create_batch_processing_components_fn=(
                ServicesBuilder.create_batch_processing_components
            ),
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
        )


def create_data_normalization_service(
    config: DataNormalizationConfig | None = None,
) -> DataNormalizationPort:
    """Create DataNormalizationService with optional configuration."""
    from bioetl.domain.services import (
        DataNormalizationConfig,
        DefaultDataNormalizationService,
    )

    return DefaultDataNormalizationService(config=config or DataNormalizationConfig())
