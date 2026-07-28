# pyright: reportTypedDictNotRequiredAccess=false
# basedpyright residual burn-down (shrink-only product surface).
"""Low-level quarantine write and event emission helpers."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import RecordQuarantined
from bioetl.domain.aggregates.quarantine_entry import QuarantineEntry
from bioetl.domain.ports import QuarantineWriteRequest
from bioetl.domain.types import BatchID, BronzeRecord, JsonDict, RunID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import QuarantinePort

async def write_quarantine_request(
    quarantine: QuarantinePort,
    request: QuarantineWriteRequest,
) -> None:
    """Write one quarantine request via the injected port."""
    await quarantine.write(
        pipeline=request["pipeline"],
        error_code=request["error_code"],
        payload=request["payload"],
        bronze_batch_id=request["bronze_batch_id"],
        run_id=request.get("run_id"),
        entry_id=request.get("entry_id"),
        metadata=request.get("metadata"),
        ingestion_ts=request["ingestion_ts"],
    )

async def write_quarantine_requests(
    quarantine: QuarantinePort,
    requests: list[QuarantineWriteRequest],
) -> None:
    """Write multiple quarantine requests via the injected port."""
    await quarantine.write_many(requests)

async def write_quarantine_request_with_events(
    *,
    quarantine: QuarantinePort,
    request: QuarantineWriteRequest,
    emitter: DomainEventEmitterProtocol | None,
    pipeline_name: str,
    error_code: str,
    error_message: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Write a quarantine request and emit its companion events."""
    await write_quarantine_request(quarantine, request)
    emit_quarantine_events(
        emitter=emitter,
        pipeline_name=pipeline_name,
        payload=request["payload"],
        error_code=error_code,
        error_message=error_message,
        batch_id=batch_id,
        run_id=run_id,
        ingestion_ts=ingestion_ts,
        metadata=request["metadata"],
    )

async def write_quarantine_requests_with_events(
    *,
    quarantine: QuarantinePort,
    requests: list[QuarantineWriteRequest],
    emitter: DomainEventEmitterProtocol | None,
    pipeline_name: str,
    error_codes: Sequence[str],
    error_messages: Sequence[str],
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Write multiple quarantine requests and emit companion events."""
    await write_quarantine_requests(quarantine, requests)
    for request, error_code, error_message in zip(
        requests,
        error_codes,
        error_messages,
        strict=True,
    ):
        emit_quarantine_events(
            emitter=emitter,
            pipeline_name=pipeline_name,
            payload=request["payload"],
            error_code=error_code,
            error_message=error_message,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
            metadata=request["metadata"],
        )

def emit_quarantine_events(
    *,
    emitter: DomainEventEmitterProtocol | None,
    pipeline_name: str,
    payload: BronzeRecord,
    error_code: str,
    error_message: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
    metadata: JsonDict | None,
) -> None:
    """Publish typed quarantine events when stable correlation IDs are present."""
    if emitter is None or run_id is None:
        return

    entry = QuarantineEntry.create(
        pipeline_name=pipeline_name,
        error_code=error_code,
        payload=payload,
        run_id=run_id,
        batch_id=batch_id,
        created_at=ingestion_ts,
        metadata=metadata,
    )
    for event in entry.collect_events():
        emitter.emit_domain_event(event)

    emitter.emit_domain_event(
        RecordQuarantined(
            occurred_at=ingestion_ts,
            run_id=run_id,
            batch_id=batch_id,
            record_id=extract_record_id(payload),
            error_code=error_code,
            error_message=error_message,
            content_hash=entry.payload_hash,
        )
    )

def extract_record_id(payload: BronzeRecord) -> str | None:
    """Best-effort extraction of a stable record identifier from raw payloads."""
    for key in (
        "entity_id",
        "activity_id",
        "assay_id",
        "molecule_id",
        "target_id",
        "record_id",
        "compound_id",
        "id",
    ):
        value = payload.get(key)
        if value is None:
            continue
        return str(value)
    return None
