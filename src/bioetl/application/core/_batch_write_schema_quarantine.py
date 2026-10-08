"""Schema-violation quarantine helper for batch write paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core._batch_write_events import BatchFailureEventContext
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    QuarantineRuntimeService,
)
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.domain.ports import LoggerPort


async def quarantine_schema_violation(
    *,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService,
    logger: LoggerPort,
    failure_context: BatchFailureEventContext,
    records: list[dict[str, object]],
    error: SchemaViolationError,
) -> None:
    layer = failure_context.layer
    writer.track_batch_failed(stage=layer, count=len(records))
    failure_context.emit(error)
    logger.warning("schema_violation_quarantined", layer=layer, errors=error.errors)
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
            for record in records
        ],
        failure_context.batch_id,
        ingestion_ts=failure_context.occurred_at,
        stage=layer,
    )
