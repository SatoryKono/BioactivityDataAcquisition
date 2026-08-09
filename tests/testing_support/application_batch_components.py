"""Application-only assembly helpers for unit-test processing components."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_processing_service import BatchProcessingComponents
from bioetl.application.core.batch_transformer import BatchTransformer
from bioetl.application.core.batch_writer import BatchWriter, BatchWriterOptions
from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriteStorageProtocol
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, TracingPort


def build_test_batch_processing_components(
    *,
    services: PipelineService,
    context: PipelineContext,
    config: RecordProcessorConfig,
    error_classifier: ErrorClassifier,
    transform_callback: Callable[..., object],
    gold_filter_callback: Callable[..., object],
    gold_transform_callback: Callable[..., object],
    gold_validator: GoldValidatorPort,
    tracer: TracingPort | None = None,
    domain_event_emitter: DomainEventEmitterProtocol | None = None,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
) -> BatchProcessingComponents:
    """Build application collaborators without crossing into composition."""
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
        ),
    )
    return BatchProcessingComponents(
        batch_metrics=batch_metrics,
        transformer=transformer,
        writer=writer,
    )
