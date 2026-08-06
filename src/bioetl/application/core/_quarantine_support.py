"""Private request builders and high-level orchestration for quarantine flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core._quarantine_metrics_support import (
    FILTERED_OUT_SILVER,
    count_dq_error_types,
    record_filtered_quarantine_metrics,
    track_processed_quarantined,
    track_quarantine_metrics,
)
from bioetl.application.core._quarantine_write_support import (
    write_quarantine_request_with_events,
    write_quarantine_requests_with_events,
)
from bioetl.domain.ports import QuarantineWriteRequest
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, RunID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.domain.ports import MetricsPort, QuarantinePort


@dataclass(frozen=True, slots=True)
class QuarantineRuntimeDependencies:
    """Shared runtime ports used by quarantine write helpers."""

    quarantine: QuarantinePort
    emitter: DomainEventEmitterProtocol | None
    pipeline_name: str
    metrics: MetricsPort | None
    pipeline_metrics: PipelineMetricsRecorder
    batch_metrics: BatchMetricsRecorderService | None
    run_type: str = "unknown"


def build_quarantine_runtime_ports(
    *,
    quarantine: QuarantinePort,
    emitter: DomainEventEmitterProtocol | None,
    pipeline_name: str,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    batch_metrics: BatchMetricsRecorderService | None,
    run_type: str = "unknown",
) -> QuarantineRuntimeDependencies:
    """Build runtime ports from quarantine manager state."""
    return QuarantineRuntimeDependencies(
        quarantine=quarantine,
        emitter=emitter,
        pipeline_name=pipeline_name,
        metrics=metrics,
        pipeline_metrics=pipeline_metrics,
        batch_metrics=batch_metrics,
        run_type=run_type,
    )


async def persist_dq_quarantine_request(
    ports: QuarantineRuntimeDependencies,
    *,
    request: QuarantineWriteRequest,
    error_type: ErrorType,
    error_details: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Write one DQ quarantine request and emit metrics/events."""
    await write_quarantine_request_with_events(
        quarantine=ports.quarantine,
        request=request,
        emitter=ports.emitter,
        pipeline_name=ports.pipeline_name,
        error_code=error_type.value,
        error_message=error_details,
        batch_id=batch_id,
        run_id=run_id,
        ingestion_ts=ingestion_ts,
    )
    track_quarantine_metrics(
        metrics=ports.metrics,
        pipeline_metrics=ports.pipeline_metrics,
        batch_metrics=ports.batch_metrics,
        pipeline_name=ports.pipeline_name,
        run_type=ports.run_type,
        error_type=error_type,
        count=1,
    )
    track_processed_quarantined(
        metrics=ports.metrics,
        batch_metrics=ports.batch_metrics,
        pipeline_name=ports.pipeline_name,
        run_type=ports.run_type,
        count=1,
    )


async def persist_dq_quarantine_requests(
    ports: QuarantineRuntimeDependencies,
    *,
    requests: list[QuarantineWriteRequest],
    records: Sequence[tuple[BronzeRecord, ErrorType, str]],
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Write multiple DQ quarantine requests and emit metrics/events."""
    await write_quarantine_requests_with_events(
        quarantine=ports.quarantine,
        requests=requests,
        emitter=ports.emitter,
        pipeline_name=ports.pipeline_name,
        error_codes=tuple(error_type.value for _, error_type, _ in records),
        error_messages=tuple(error_details for _, _, error_details in records),
        batch_id=batch_id,
        run_id=run_id,
        ingestion_ts=ingestion_ts,
    )
    for reason, count in count_dq_error_types(records).items():
        track_quarantine_metrics(
            metrics=ports.metrics,
            pipeline_metrics=ports.pipeline_metrics,
            batch_metrics=ports.batch_metrics,
            pipeline_name=ports.pipeline_name,
            run_type=ports.run_type,
            error_type=reason,
            count=count,
        )
    track_processed_quarantined(
        metrics=ports.metrics,
        batch_metrics=ports.batch_metrics,
        pipeline_name=ports.pipeline_name,
        run_type=ports.run_type,
        count=len(requests),
    )


async def persist_filtered_quarantine_request(
    ports: QuarantineRuntimeDependencies,
    *,
    request: QuarantineWriteRequest,
    error_details: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Write one filter-rejection quarantine request and emit metrics/events."""
    await write_quarantine_request_with_events(
        quarantine=ports.quarantine,
        request=request,
        emitter=ports.emitter,
        pipeline_name=ports.pipeline_name,
        error_code=FILTERED_OUT_SILVER,
        error_message=error_details,
        batch_id=batch_id,
        run_id=run_id,
        ingestion_ts=ingestion_ts,
    )
    record_filtered_quarantine_metrics(
        metrics=ports.metrics,
        pipeline_metrics=ports.pipeline_metrics,
        count=1,
    )


async def persist_filtered_quarantine_requests(
    ports: QuarantineRuntimeDependencies,
    *,
    requests: list[QuarantineWriteRequest],
    reasons: Sequence[str],
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> None:
    """Write multiple filter-rejection quarantine requests and emit metrics."""
    await write_quarantine_requests_with_events(
        quarantine=ports.quarantine,
        requests=requests,
        emitter=ports.emitter,
        pipeline_name=ports.pipeline_name,
        error_codes=tuple(FILTERED_OUT_SILVER for _ in reasons),
        error_messages=tuple(reasons),
        batch_id=batch_id,
        run_id=run_id,
        ingestion_ts=ingestion_ts,
    )
    record_filtered_quarantine_metrics(
        metrics=ports.metrics,
        pipeline_metrics=ports.pipeline_metrics,
        count=len(requests),
    )
