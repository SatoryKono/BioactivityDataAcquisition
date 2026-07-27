"""Failed record-transform attempt helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_transformer_attempt_success import empty_outcome
from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.services.debug_export_service import DebugExportService
    from bioetl.domain.config import DQConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID, BronzeRecord, ErrorType


def _resolve_invalid_record_policy(dq_config: DQConfig | None) -> str:
    """Resolve invalid-record policy with runtime-safe default."""
    if dq_config is None:
        return "quarantine"
    return dq_config.invalid_record_policy


def _transform_failure_entity_id(raw_record: BronzeRecord) -> object:
    """Resolve the best-effort entity identifier for transform failure logs."""
    return (
        raw_record.get("publication_id")
        or raw_record.get("document_chembl_id")
        or raw_record.get("activity_id")
    )


@dataclass(frozen=True, slots=True)
class _FilteredOutHandlingContext:
    """Captured state needed to apply the filtered-out handling policy."""

    batch_metrics: BatchMetricsRecorderService
    dq_config: DQConfig | None
    raw_record: BronzeRecord
    debug_export_service: DebugExportService | None
    index: int


def _build_filtered_out_handling_context(
    batch_metrics: BatchMetricsRecorderService,
    dq_config: DQConfig | None,
    raw_record: BronzeRecord,
    debug_export_service: DebugExportService | None,
    index: int,
) -> _FilteredOutHandlingContext:
    """Capture filtered-out handling inputs for reuse at call sites."""
    return _FilteredOutHandlingContext(
        batch_metrics=batch_metrics,
        dq_config=dq_config,
        raw_record=raw_record,
        debug_export_service=debug_export_service,
        index=index,
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


def handle_filtered_out_error(
    error: FilteredOutError,
    handling_context: _FilteredOutHandlingContext,
) -> RecordTransformOutcome:
    """Handle a Silver filter rejection according to invalid-record policy."""
    batch_metrics = handling_context.batch_metrics
    dq_config = handling_context.dq_config
    raw_record = handling_context.raw_record
    debug_export_service = handling_context.debug_export_service
    index = handling_context.index
    batch_metrics.track_processed_records("filtered_out", 1)
    batch_metrics.track_silver_filter_rejection(error.details or None)
    policy = _resolve_invalid_record_policy(dq_config)
    if debug_export_service is not None:
        debug_export_service.record_filtered_out(
            raw_record=raw_record,
            record_index=index,
            reason=str(error),
            details=error.details or None,
            policy=policy,
        )
    if policy == "skip":
        return empty_outcome()
    if policy == "fail":
        raise error
    return RecordTransformOutcome(
        silver_record=None,
        gold_record=None,
        filtered_entry=FilteredQuarantineEntry(
            record=raw_record,
            reason=str(error),
            details=error.details or None,
        ),
    )


def handle_transform_processing_error(
    error: Exception,
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
    index: int,
    error_classifier: ErrorClassifier,
    batch_metrics: BatchMetricsRecorderService,
    dq_config: DQConfig | None,
    debug_export_service: DebugExportService | None,
) -> RecordTransformOutcome:
    """Handle transform exceptions and route data-quality failures."""
    _log_transform_record_failure(
        context=context,
        batch_id=batch_id,
        raw_record=raw_record,
        index=index,
        error=error,
    )
    error_type = error_classifier.classify(error)
    if not error_type.is_data_quality():
        raise error
    return handle_data_quality_transform_error(
        error,
        error_type=error_type,
        batch_metrics=batch_metrics,
        dq_config=dq_config,
        raw_record=raw_record,
        debug_export_service=debug_export_service,
        index=index,
    )


def handle_data_quality_transform_error(
    error: Exception,
    *,
    error_type: ErrorType,
    batch_metrics: BatchMetricsRecorderService,
    dq_config: DQConfig | None,
    raw_record: BronzeRecord,
    debug_export_service: DebugExportService | None,
    index: int,
) -> RecordTransformOutcome:
    """Apply invalid-record policy to a data-quality transform error."""
    batch_metrics.track_error("transform", error_type)
    policy = _resolve_invalid_record_policy(dq_config)
    if debug_export_service is not None:
        debug_export_service.record_data_quality_failure(
            raw_record=raw_record,
            record_index=index,
            error_type=error_type,
            error_details=str(error),
            policy=policy,
        )
    if policy == "fail":
        raise error
    if policy == "skip":
        return empty_outcome()
    batch_metrics.track_quarantined_records(error_type, 1)
    return RecordTransformOutcome(
        silver_record=None,
        gold_record=None,
        dq_entry=DQQuarantineEntry(raw_record, error_type, str(error)),
    )


__all__ = [
    "handle_data_quality_transform_error",
    "handle_filtered_out_error",
    "handle_transform_processing_error",
]
