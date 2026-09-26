"""Schema-violation quarantine helper for batch write paths."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    QuarantineRuntimeService,
)
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID, ErrorType, RunID

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort


async def quarantine_schema_violation(
    *,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService,
    logger: LoggerPort,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    run_id: RunID | None,
    layer: str,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    error: SchemaViolationError,
) -> None:
    from bioetl.application.core._batch_write_support import emit_batch_failed

    writer.track_batch_failed(stage=layer, count=len(records))
    emit_batch_failed(
        emitter=domain_event_emitter,
        run_id=run_id,
        batch_id=batch_id,
        layer=layer,
        error=error,
        occurred_at=ingestion_ts,
        logger=logger,
    )
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
        batch_id,
        ingestion_ts=ingestion_ts,
        stage=layer,
    )
