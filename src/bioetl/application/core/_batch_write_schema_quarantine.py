"""Schema-violation quarantine helper for batch write paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core._batch_write_events import BatchWriteEventContext
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    QuarantineRuntimeService,
)
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter


async def quarantine_schema_violation(
    *,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService,
    event_context: BatchWriteEventContext,
    records: list[dict[str, object]],
    error: SchemaViolationError,
) -> None:
    layer = event_context.layer
    remaining = _records_without_outcome_quarantine(writer, records, layer)
    event_context.emit_failed(error)
    event_context.logger.warning(
        "schema_violation_quarantined", layer=layer, errors=error.errors
    )
    if not remaining:
        return
    writer.track_batch_failed(stage=layer, count=len(remaining))
    reason_code = (
        "gold_contract_schema_failure"
        if layer == "gold"
        else ErrorType.SCHEMA_VIOLATION.value
    )
    await quarantine_manager.quarantine_records(
        [
            DQQuarantineEntry(
                record=record,
                error_type=ErrorType.SCHEMA_VIOLATION,
                error_details=f"Schema violation in {layer}: {error.errors}",
                reason_code=reason_code,
            )
            for record in remaining
        ],
        event_context.batch_id,
        ingestion_ts=event_context.occurred_at,
        stage=layer,
    )


def _records_without_outcome_quarantine(
    writer: BatchWriter,
    records: list[dict[str, object]],
    layer: str,
) -> list[dict[str, object]]:
    """Drop rows already flushed by the Gold outcome channel."""
    if layer != "gold":
        return records
    raw = getattr(writer, "_gold_outcome_quarantine_indexes", ())
    writer._gold_outcome_quarantine_indexes = ()
    if not isinstance(raw, tuple):
        return records
    indexes = {
        index for index in raw if isinstance(index, int) and not isinstance(index, bool)
    }
    if not indexes:
        return records
    return [record for index, record in enumerate(records) if index not in indexes]
