"""Private request, metrics, and event helpers for quarantine flows."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import RecordQuarantined
from bioetl.domain.aggregates.quarantine_entry import QuarantineEntry
from bioetl.domain.ports import QuarantineWriteRequest
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, JsonDict, RunID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterPort,
    )
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.domain.ports import MetricsPort, QuarantinePort


FILTERED_OUT_SILVER = "FILTERED_OUT_SILVER"


def build_filtered_quarantine_metadata(
    *,
    reason: str,
    details: JsonDict | None,
) -> JsonDict:
    """Build canonical quarantine metadata for Silver filter rejections."""
    error_details: JsonDict = {"message": reason}
    if details:
        error_details.update(
            {key: value for key, value in details.items() if key != "message"}
        )
    return {
        "error_details": error_details,
        "classification": "filter_rejection",
        "quarantine_category": "silver_filter",
    }


def build_dq_quarantine_request(
    *,
    pipeline_name: str,
    record: BronzeRecord,
    error_type: ErrorType,
    error_details: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> QuarantineWriteRequest:
    """Build one DQ quarantine write request."""
    return {
        "pipeline": pipeline_name,
        "error_code": error_type.value,
        "payload": record,
        "bronze_batch_id": batch_id,
        "run_id": run_id,
        "metadata": {"error_details": {"message": error_details}},
        "ingestion_ts": ingestion_ts,
    }


def build_filtered_quarantine_request(
    *,
    pipeline_name: str,
    record: BronzeRecord,
    reason: str,
    details: JsonDict | None,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> QuarantineWriteRequest:
    """Build one filter-rejection quarantine write request."""
    return {
        "pipeline": pipeline_name,
        "error_code": FILTERED_OUT_SILVER,
        "payload": record,
        "bronze_batch_id": batch_id,
        "run_id": run_id,
        "metadata": build_filtered_quarantine_metadata(
            reason=reason,
            details=details,
        ),
        "ingestion_ts": ingestion_ts,
    }


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
    emitter: DomainEventEmitterPort | None,
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
    emitter: DomainEventEmitterPort | None,
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


def track_quarantine_metrics(
    *,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    pipeline_name: str,
    error_type: ErrorType,
    count: int,
) -> None:
    """Emit quarantine metrics through both legacy and current metric APIs."""
    if metrics is None:
        return

    track_quarantined_records = getattr(metrics, "track_quarantined_records", None)
    if callable(track_quarantined_records):
        track_quarantined_records(error_type, count)

    metrics.increment_counter(
        "bioetl_dq_records_quarantined_total",
        count,
        {"pipeline": pipeline_name, "error_type": error_type.value},
    )
    pipeline_metrics.record_quarantine_records(
        reason=error_type.value,
        count=count,
    )


def track_processed_quarantined(
    *,
    metrics: MetricsPort | None,
    pipeline_name: str,
    count: int,
) -> None:
    """Emit processed-record metrics for the quarantine stage."""
    if metrics is None:
        return

    track_processed_records = getattr(metrics, "track_processed_records", None)
    if callable(track_processed_records):
        track_processed_records("quarantined", count)

    metrics.increment_counter(
        "bioetl_records_processed_total",
        count,
        {"pipeline": pipeline_name, "stage": "quarantined"},
    )


def count_dq_error_types(
    records: Sequence[tuple[BronzeRecord, ErrorType, str]],
) -> Counter[ErrorType]:
    """Count DQ quarantine entries by error type."""
    return Counter(error_type for _, error_type, _ in records)


def record_filtered_quarantine_metrics(
    *,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    count: int,
) -> None:
    """Emit metrics for filter-rejected records."""
    if metrics is None:
        return
    pipeline_metrics.record_quarantine_records(
        reason=FILTERED_OUT_SILVER,
        count=count,
    )


def emit_quarantine_events(
    *,
    emitter: DomainEventEmitterPort | None,
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
