"""Quarantine persistence helpers for batch transformation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.batch_processing_runtime import (
    OPERATION_ERRORS as SHARED_OPERATION_ERRORS,
)
from bioetl.application.core.batch_transformer_state import (
    RecordTransformOutcome,
    TransformedRecord,
)
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
    QuarantineRuntimeService,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BatchID

QUARANTINE_WRITE_WARN_ONLY_ERRORS = SHARED_OPERATION_ERRORS

async def flush_filtered_records(
    *,
    context: PipelineContext,
    quarantine_manager: QuarantineRuntimeService,
    records: list[FilteredQuarantineEntry],
    batch_id: BatchID,
) -> int:
    """Persist Silver filter rejections to quarantine without blocking progress."""
    if not records:
        return 0
    try:
        await quarantine_manager.quarantine_filtered_records(
            records,
            batch_id,
            run_id=context.run_id,
            ingestion_ts=context.started_at,
        )
        return 0
    except QUARANTINE_WRITE_WARN_ONLY_ERRORS as exc:
        context.logger.error(
            "filter_quarantine_write_failed",
            batch_id=str(batch_id),
            records=len(records),
            error=str(exc),
        )
        return len(records)

async def flush_dq_records(
    *,
    context: PipelineContext,
    quarantine_manager: QuarantineRuntimeService,
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
            run_id=context.run_id,
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

async def route_single_transform_attempt(
    *,
    context: PipelineContext,
    quarantine_manager: QuarantineRuntimeService,
    attempt: RecordTransformOutcome,
    batch_id: BatchID,
) -> TransformedRecord:
    """Route one transform attempt to a public single-record result."""
    if attempt.silver_record is not None:
        return TransformedRecord(
            silver_record=attempt.silver_record,
            gold_record=attempt.gold_record,
            is_quarantined=False,
            gold_excluded_by_contract=attempt.gold_excluded_by_contract,
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
