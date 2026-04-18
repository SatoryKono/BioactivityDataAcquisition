from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.wiring.runtime import (
    BatchExecutor,
    BatchProcessingComponents,
    CheckpointManagerService,
    ContentHashPolicyByVersion,
    GoldFilterCallback,
    GoldTransformCallback,
    PipelineService,
    RecordProcessor,
    RecordProcessorConfig,
    ShutdownSignal,
    TransformCallback,
)
from bioetl.composition.factories.services._builder_record_processor_support import (
    create_record_processor_impl,
)
from bioetl.composition.factories.services.callbacks import (
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.services.pipeline_builder import (
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
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import BasePipeline
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterPort,
    )
    from bioetl.domain.config import DQConfig, MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        CheckpointPort,
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import (
        GoldSchemaPolicyByVersion,
        GoldSchemaType,
        RunID,
        ScdConfig,
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
        domain_event_emitter: DomainEventEmitterPort | None = None,
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
        checkpoint_compatibility_service: object | None = None,
        current_metadata: CheckpointMetadata | None = None,
        compatibility_policy: Literal[
            "observe", "soft_fail", "hard_fail"
        ] = "soft_fail",
    ) -> CheckpointManagerService:
        return create_checkpoint_manager(
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

    @staticmethod
    def create_record_processor(
        services: PipelineService,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        silver_schema: pa.Schema | None,
        gold_schema: GoldSchemaType,
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
        scd_config: ScdConfig | None = None,
        content_hash_include_fields: frozenset[str] = frozenset(),
        content_hash_exclude_fields: frozenset[str] = frozenset(),
        content_hash_policy_by_version: ContentHashPolicyByVersion | None = None,
        gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None = None,
    ) -> RecordProcessor:
        return create_record_processor_impl(
            services_builder=ServicesBuilder,
            services=services,
            context=context,
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=dq_config,
            primary_keys=primary_keys,
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            tracer=tracer,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            column_groups=column_groups,
            scd_config=scd_config,
            content_hash_include_fields=content_hash_include_fields,
            content_hash_exclude_fields=content_hash_exclude_fields,
            content_hash_policy_by_version=content_hash_policy_by_version,
            gold_schema_policy_by_version=gold_schema_policy_by_version,
            record_processor_config_cls=RecordProcessorConfig,
            table_config_cls=TableConfig,
            gold_validator_factory=PanderaGoldValidator,
            record_processor_cls=RecordProcessor,
        )

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
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: GoldSchemaType,
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
        domain_event_emitter: DomainEventEmitterPort | None = None,
    ) -> BatchExecutor:
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
            domain_event_emitter=domain_event_emitter,
        )
