"""Per-record transform helpers for batch transformation."""

from __future__ import annotations

from inspect import isawaitable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_runtime_failure_policy import OPERATION_ERRORS
from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.core.record_normalization_processor import (
        RecordNormalizationProcessor,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID

TRANSFORM_PROCESSING_ERRORS = OPERATION_ERRORS


def bind_record_context(
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
) -> PipelineContext:
    """Create a per-record logger context for transformation."""
    return context.with_source_batch_id(batch_id).bind_logger(
        batch_id=str(batch_id),
        entity_id=raw_record.get("activity_id"),
    )


def _empty_outcome() -> RecordTransformOutcome:
    """Return an empty transform outcome."""
    return RecordTransformOutcome(silver_record=None, gold_record=None)


def _finalize_transformed_record(
    *,
    transformed: dict[str, object] | PreSilverRecord | None,
    normalization_processor: RecordNormalizationProcessor | None,
    context: PipelineContext,
    index: int,
) -> dict[str, object] | None:
    """Finalize transform output through the normalization stage."""
    if transformed is None:
        return None
    if isinstance(transformed, PreSilverRecord):
        if normalization_processor is None:
            raise RuntimeError("PreSilverRecord requires RecordNormalizationProcessor")
        finalized_record: dict[str, object] | None = (
            normalization_processor.finalize_pre_silver(
                transformed,
                context,
                index,
            )
        )
        return finalized_record
    if normalization_processor is None:
        return transformed
    normalized_record: dict[str, object] | None = (
        normalization_processor.normalize_record(transformed)
    )
    return normalized_record


def _build_gold_record(
    *,
    context: PipelineContext,
    silver_record: dict[str, object],
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
) -> dict[str, object] | None:
    """Create a Gold record when the finalized Silver record passes filtering."""
    if not gold_filter(context, silver_record):
        return None
    gold_record = cast(
        dict[str, object] | None,
        gold_transform(context, silver_record),
    )
    return gold_record


def _transform_failure_entity_id(raw_record: BronzeRecord) -> object:
    """Resolve the best-effort entity identifier for transform failure logs."""
    return (
        raw_record.get("publication_id")
        or raw_record.get("document_chembl_id")
        or raw_record.get("activity_id")
    )


def _log_transform_record_failure(
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
    index: int,
    error: Exception,
) -> None:
    """Emit a structured transform-failure log with record context."""
    context.logger.exception(
        "transform_record_failed",
        pipeline=context.pipeline_name,
        batch_id=str(batch_id),
        record_index=index,
        source_batch_id=str(context.source_batch_id)
        if context.source_batch_id is not None
        else None,
        error_type=type(error).__name__,
        error=str(error),
        entity_id=_transform_failure_entity_id(raw_record),
    )


async def transform_record_attempt(
    *,
    context: PipelineContext,
    error_classifier: ErrorClassifier,
    batch_metrics: BatchMetricsRecorderService,
    transform: TransformCallback,
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
    normalization_processor: RecordNormalizationProcessor | None,
    raw_record: BronzeRecord,
    batch_id: BatchID,
    index: int,
) -> RecordTransformOutcome:
    """Transform one record and classify it before quarantine persistence."""
    record_context = bind_record_context(
        context=context,
        batch_id=batch_id,
        raw_record=raw_record,
    )

    try:
        transformed_result = transform(record_context, raw_record, index)
        transformed = (
            await transformed_result
            if isawaitable(transformed_result)
            else transformed_result
        )
        finalized_record = _finalize_transformed_record(
            transformed=transformed,
            normalization_processor=normalization_processor,
            context=record_context,
            index=index,
        )
        if finalized_record is None:
            return _empty_outcome()

        gold_record = _build_gold_record(
            context=record_context,
            silver_record=finalized_record,
            gold_filter=gold_filter,
            gold_transform=gold_transform,
        )

        return RecordTransformOutcome(
            silver_record=finalized_record,
            gold_record=gold_record,
        )
    except FilteredOutError as error:
        batch_metrics.track_processed_records("filtered_out", 1)
        batch_metrics.track_silver_filter_rejection(error.details or None)
        return RecordTransformOutcome(
            silver_record=None,
            gold_record=None,
            filtered_entry=FilteredQuarantineEntry(
                record=raw_record,
                reason=str(error),
                details=error.details or None,
            ),
        )
    except TRANSFORM_PROCESSING_ERRORS as error:
        _log_transform_record_failure(
            context=record_context,
            batch_id=batch_id,
            raw_record=raw_record,
            index=index,
            error=error,
        )
        error_type = error_classifier.classify(error)
        if error_type.is_data_quality():
            batch_metrics.track_error("transform", error_type)
            batch_metrics.track_quarantined_records(error_type, 1)
            return RecordTransformOutcome(
                silver_record=None,
                gold_record=None,
                dq_entry=DQQuarantineEntry(raw_record, error_type, str(error)),
            )
        raise
