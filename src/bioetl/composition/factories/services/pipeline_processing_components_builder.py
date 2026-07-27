"""Assembly helpers for batch processing components."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.core.wiring.runtime import (
    BatchMetricsRecorderService,
    BatchProcessingComponents,
    BatchTransformer,
    BatchWriter,
    BatchWriterOptions,
    GoldFilterCallback,
    GoldTransformCallback,
    PipelineService,
    QuarantineRuntimeService,
    RecordNormalizationProcessor,
    RecordProcessorConfig,
    TransformCallback,
)
from bioetl.application.services.debug_export_service import (
    DebugExportConfig,
    DebugExportService,
)
from bioetl.infrastructure.export.debug_export_adapter import DebugExportAdapter

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriteStorageProtocol
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, TracingPort


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
    """Create batch metrics, transformer, and writer via composition DI."""
    batch_metrics = BatchMetricsRecorderService(
        services.metrics,
        f"{config.provider}_{config.entity_type}",
        context.run_type.value,
    )
    quarantine_manager = QuarantineRuntimeService(
        quarantine_port=services.quarantine,
        pipeline_name=config.pipeline_name,
        metrics=services.metrics,
        batch_metrics=batch_metrics,
        run_type=context.run_type.value,
        domain_event_emitter=domain_event_emitter,
    )
    normalization_processor = (
        RecordNormalizationProcessor(
            provider=config.provider,
            entity_type=config.entity_type,
            rule_set=config.normalization_rule_set,
            allow_compatibility_fallback=config.allow_compatibility_fallback,
            content_hash_include_fields=config.content_hash_include_fields,
            content_hash_exclude_fields=config.content_hash_exclude_fields,
            content_hash_policy_by_version=config.content_hash_policy_by_version,
        )
        if config.normalization_enabled
        else None
    )
    debug_export_service = _build_debug_export_service(config=config, context=context)
    transformer = BatchTransformer(
        context=context,
        config=config,
        runtime={
            "error_classifier": error_classifier,
            "quarantine_manager": quarantine_manager,
            "batch_metrics": batch_metrics,
        },
        callbacks={
            "transform_callback": transform_callback,
            "gold_filter_callback": gold_filter_callback,
            "gold_transform_callback": gold_transform_callback,
        },
        normalization_processor=normalization_processor,
        debug_export_service=debug_export_service,
    )
    column_orderer = (
        ColumnOrderService(context.logger, column_groups=config.column_groups)
        if config.column_groups
        else None
    )
    writer = BatchWriter(
        storage=cast("BatchWriteStorageProtocol", services.storage),
        context=context,
        config=config,
        gold_validator=gold_validator,
        error_classifier=error_classifier,
        batch_metrics=batch_metrics,
        options=BatchWriterOptions(
            tracer=tracer,
            lock_validator=lock_validator,
            column_orderer=column_orderer,
            debug_export_service=debug_export_service,
        ),
    )
    return BatchProcessingComponents(
        batch_metrics=batch_metrics,
        transformer=transformer,
        writer=writer,
    )


def _build_debug_export_service(
    *,
    config: RecordProcessorConfig,
    context: PipelineContext,
) -> DebugExportService | None:
    """Build optional debug export service from processor config."""
    raw_debug_export_config = getattr(config, "debug_export_config", None)
    debug_export_config = (
        raw_debug_export_config
        if isinstance(raw_debug_export_config, DebugExportConfig)
        else None
    )
    if debug_export_config is None or not is_dataclass(debug_export_config):
        return None
    return DebugExportService(
        config=replace(
            debug_export_config,
            workflow_id=getattr(context, "workflow_id", "standalone"),
        ),
        run_id=context.run_id,
        pipeline_id=config.pipeline_name,
        provider_id=config.provider,
        writer=DebugExportAdapter(),
    )


__all__ = ["create_batch_processing_components"]
