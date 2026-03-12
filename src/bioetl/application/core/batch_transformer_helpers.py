"""Internal helper functions for batch transformation orchestration."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_finalization import (
    check_dq_thresholds as _check_dq_thresholds,
)
from bioetl.application.core.batch_transformer_finalization import (
    finalize_batch_transform_result as _finalize_batch_transform_result,
)
from bioetl.application.core.batch_transformer_finalization import (
    finalize_stream_transform_result as _finalize_stream_transform_result,
)
from bioetl.application.core.batch_transformer_state import (
    RecordTransformOutcome,
    TransformAggregationState,
    TransformedRecord,
    TransformResult,
    accumulate_stream_transform_result,
    accumulate_transform_outcome,
    apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state,
    build_transform_result,
    create_transform_aggregation_state,
)
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
    QuarantineManagerService,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types import BatchID


__all__ = [
    "RecordTransformOutcome",
    "TransformAggregationState",
    "TransformResult",
    "TransformedRecord",
    "accumulate_stream_transform_result",
    "accumulate_transform_outcome",
    "apply_stream_transform_result_to_state",
    "apply_transform_outcome_to_state",
    "bind_record_context",
    "build_transform_result",
    "check_dq_thresholds",
    "create_transform_aggregation_state",
    "finalize_batch_transform_result",
    "finalize_stream_transform_result",
    "flush_dq_records",
    "flush_filtered_records",
    "route_single_transform_attempt",
    "transform_record_attempt",
    "yield_control_if_needed",
]


TRANSFORM_PROCESSING_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)
QUARANTINE_WRITE_WARN_ONLY_ERRORS = TRANSFORM_PROCESSING_ERRORS
YIELD_INTERVAL_SECONDS = 0.5


async def yield_control_if_needed(last_yield_at: float) -> float:
    """Cooperatively yield to the event loop during CPU-heavy transforms."""
    now = time.monotonic()
    if now - last_yield_at < YIELD_INTERVAL_SECONDS:
        return last_yield_at
    await asyncio.sleep(0)
    return time.monotonic()


async def flush_filtered_records(
    *,
    context: PipelineContext,
    quarantine_manager: QuarantineManagerService,
    records: list[FilteredQuarantineEntry],
    batch_id: BatchID,
) -> int:
    """Persist filtered-out records without blocking pipeline progress."""
    if not records:
        return 0
    try:
        await quarantine_manager.quarantine_filtered_records(
            records,
            batch_id,
            ingestion_ts=context.started_at,
        )
        return 0
    except QUARANTINE_WRITE_WARN_ONLY_ERRORS as exc:
        context.logger.error(
            "filtered_quarantine_write_failed",
            batch_id=str(batch_id),
            records=len(records),
            error=str(exc),
        )
        return len(records)


async def flush_dq_records(
    *,
    context: PipelineContext,
    quarantine_manager: QuarantineManagerService,
    records: list[DQQuarantineEntry],
    batch_id: BatchID,
) -> int:
    """Persist DQ quarantine records without failing the batch."""
    if not records:
        return 0
    try:
        await quarantine_manager.quarantine_records(
            records,
            batch_id,
            ingestion_ts=context.started_at,
        )
        return 0
    except QUARANTINE_WRITE_WARN_ONLY_ERRORS as exc:
        context.logger.error(
            "dq_quarantine_write_failed",
            batch_id=str(batch_id),
            records=len(records),
            error=str(exc),
        )
        return len(records)


def bind_record_context(
    *,
    context: PipelineContext,
    batch_id: BatchID,
    raw_record: BronzeRecord,
) -> PipelineContext:
    """Create a per-record logger context for transformation."""
    return context.bind_logger(
        batch_id=str(batch_id),
        entity_id=raw_record.get("activity_id"),
    )


async def transform_record_attempt(
    *,
    context: PipelineContext,
    error_classifier: ErrorClassifier,
    batch_metrics: BatchMetricsRecorderService,
    transform: TransformCallback,
    gold_filter: GoldFilterCallback,
    gold_transform: GoldTransformCallback,
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
        transformed = await transform(record_context, raw_record, index)
        if transformed is None:
            return RecordTransformOutcome(
                silver_record=None,
                gold_record=None,
            )

        gold_record = None
        if gold_filter(record_context, transformed):
            gold_record = gold_transform(record_context, transformed)

        return RecordTransformOutcome(
            silver_record=transformed,
            gold_record=gold_record,
        )
    except FilteredOutError as error:
        batch_metrics.track_processed_records("filtered_out", 1)
        return RecordTransformOutcome(
            silver_record=None,
            gold_record=None,
            filtered_entry=FilteredQuarantineEntry(raw_record, str(error)),
        )
    except TRANSFORM_PROCESSING_ERRORS as error:
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


async def route_single_transform_attempt(
    *,
    context: PipelineContext,
    quarantine_manager: QuarantineManagerService,
    attempt: RecordTransformOutcome,
    batch_id: BatchID,
) -> TransformedRecord:
    """Route one transform attempt to a public single-record result."""
    if attempt.silver_record is not None:
        return TransformedRecord(
            silver_record=attempt.silver_record,
            gold_record=attempt.gold_record,
            is_quarantined=False,
        )
    if attempt.filtered_entry is not None:
        failed = await flush_filtered_records(
            context=context,
            quarantine_manager=quarantine_manager,
            records=[attempt.filtered_entry],
            batch_id=batch_id,
        )
        return TransformedRecord(
            silver_record=None,
            gold_record=None,
            is_quarantined=False,
            is_filtered_out=True,
            quarantine_write_failed=failed > 0,
        )
    if attempt.dq_entry is not None:
        failed = await flush_dq_records(
            context=context,
            quarantine_manager=quarantine_manager,
            records=[attempt.dq_entry],
            batch_id=batch_id,
        )
        return TransformedRecord(
            silver_record=None,
            gold_record=None,
            is_quarantined=True,
            quarantine_write_failed=failed > 0,
        )
    return TransformedRecord(
        silver_record=None,
        gold_record=None,
        is_quarantined=False,
    )


async def finalize_batch_transform_result(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    quarantine_manager: QuarantineManagerService,
    state: TransformAggregationState,
    batch_id: BatchID,
    records: list[BronzeRecord],
) -> TransformResult:
    """Flush batch quarantine buffers, validate thresholds, and build result."""
    return await _finalize_batch_transform_result(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        state=state,
        records=records,
        flush_filtered_records=lambda: flush_filtered_records(
            context=context,
            quarantine_manager=quarantine_manager,
            records=state.filtered_records,
            batch_id=batch_id,
        ),
        flush_dq_records=lambda: flush_dq_records(
            context=context,
            quarantine_manager=quarantine_manager,
            records=state.dq_records,
            batch_id=batch_id,
        ),
    )


def finalize_stream_transform_result(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    state: TransformAggregationState,
    records: list[BronzeRecord],
) -> TransformResult:
    """Validate streaming thresholds and build result."""
    return _finalize_stream_transform_result(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        state=state,
        records=records,
    )


def check_dq_thresholds(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    records: list[BronzeRecord],
    quarantined_count: int,
) -> None:
    """Check DQ thresholds and raise or warn as appropriate."""
    _check_dq_thresholds(
        context=context,
        config=config,
        batch_metrics=batch_metrics,
        records=records,
        quarantined_count=quarantined_count,
    )
