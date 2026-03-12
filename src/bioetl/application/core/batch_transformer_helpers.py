"""Internal helper functions for batch transformation orchestration."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
    QuarantineManagerService,
)
from bioetl.domain.exceptions import BioETLError, DataQualityThresholdError
from bioetl.domain.types import BronzeRecord, GoldRecord

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
    "TransformResult",
    "TransformedRecord",
    "RecordTransformOutcome",
    "accumulate_transform_outcome",
    "accumulate_stream_transform_result",
    "bind_record_context",
    "check_dq_thresholds",
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


@dataclass(frozen=True, slots=True)
class RecordTransformOutcome:
    """Internal outcome of transforming one record before quarantine flush."""

    silver_record: BronzeRecord | None
    gold_record: GoldRecord | None
    filtered_entry: FilteredQuarantineEntry | None = None
    dq_entry: DQQuarantineEntry | None = None


@dataclass(frozen=True, slots=True)
class TransformResult:
    """Result of batch transformation."""

    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int = 0
    records_quarantine_failed: int = 0


@dataclass(frozen=True, slots=True)
class TransformedRecord:
    """Single transformed record with routing info."""

    silver_record: BronzeRecord | None
    gold_record: GoldRecord | None
    is_quarantined: bool
    is_filtered_out: bool = False
    quarantine_write_failed: bool = False


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


def accumulate_transform_outcome(
    *,
    attempt: RecordTransformOutcome,
    silver_records: list[BronzeRecord],
    gold_records: list[GoldRecord],
    filtered_records: list[FilteredQuarantineEntry],
    dq_records: list[DQQuarantineEntry],
) -> tuple[int, int]:
    """Route a transformed-record outcome into batch accumulators."""
    if attempt.filtered_entry is not None:
        filtered_records.append(attempt.filtered_entry)
        return 0, 1
    if attempt.dq_entry is not None:
        dq_records.append(attempt.dq_entry)
        return 1, 0
    if attempt.silver_record is not None:
        silver_records.append(attempt.silver_record)
        if attempt.gold_record is not None:
            gold_records.append(attempt.gold_record)
    return 0, 0


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


def accumulate_stream_transform_result(
    *,
    result: TransformedRecord,
    silver_records: list[BronzeRecord],
    gold_records: list[GoldRecord],
) -> tuple[int, int, int]:
    """Route a single streaming transform result into accumulators."""
    quarantine_failed_delta = int(result.quarantine_write_failed)
    if result.is_quarantined:
        return 1, 0, quarantine_failed_delta
    if result.is_filtered_out:
        return 0, 1, quarantine_failed_delta
    if result.silver_record is not None:
        silver_records.append(result.silver_record)
        if result.gold_record is not None:
            gold_records.append(result.gold_record)
    return 0, 0, quarantine_failed_delta


def check_dq_thresholds(
    *,
    context: PipelineContext,
    config: RecordProcessorConfig,
    batch_metrics: BatchMetricsRecorderService,
    records: list[BronzeRecord],
    quarantined_count: int,
) -> None:
    """Check DQ thresholds and raise or warn as appropriate."""
    if not records:
        return

    total_count = len(records)
    error_rate = quarantined_count / total_count if total_count > 0 else 0.0
    dq_config = config.dq_config

    if not dq_config:
        return

    if (
        dq_config.hard_fail_threshold
        and dq_config.hard_fail_threshold < 1.0
        and error_rate >= dq_config.hard_fail_threshold
    ):
        batch_metrics.track_dq_validation_failure(
            stage="transform",
            severity="hard_fail",
        )
        raise DataQualityThresholdError(error_rate, dq_config.hard_fail_threshold)

    if (
        dq_config.soft_fail_threshold
        and error_rate >= dq_config.soft_fail_threshold
    ):
        context.logger.warning(
            "DQ Soft Threshold exceeded",
            error_rate=round(error_rate, 4),
            threshold=dq_config.soft_fail_threshold,
            quarantined_count=quarantined_count,
            total_count=total_count,
            hard_threshold=dq_config.hard_fail_threshold,
            pipeline=config.pipeline_name,
        )
        batch_metrics.track_dq_validation_failure(
            stage="transform",
            severity="soft_fail",
        )
