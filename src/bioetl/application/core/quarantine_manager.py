"""Runtime quarantine service for ETL pipelines.

Refactored per ADR-005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from bioetl.application.core._quarantine_manager_support import (
    QuarantineManagerSupportMixin,
)
from bioetl.application.core._quarantine_support import (
    build_dq_quarantine_request,
    count_dq_error_types,
    track_processed_quarantined,
    track_quarantine_metrics,
    write_quarantine_request_with_events,
    write_quarantine_requests_with_events,
)
from bioetl.application.observability.domain_event_emitter import (
    DomainEventEmitterProtocol,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.ports import MetricsPort, QuarantinePort
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, JsonDict, RunID

from .batch_metrics import BatchMetricsRecorderService


class DQQuarantineEntry(NamedTuple):
    """A record that failed data-quality checks."""

    record: BronzeRecord
    error_type: ErrorType
    error_details: str


class FilteredQuarantineEntry(NamedTuple):
    """A record excluded by Silver filters."""

    record: BronzeRecord
    reason: str
    details: JsonDict | None = None


class QuarantineRuntimeService(QuarantineManagerSupportMixin):
    """Write records that fail processing to quarantine storage.

    Admin/operator inspection and purge workflows live in
    ``application.services.quarantine_service.QuarantineService``.
    """

    def __init__(
        self,
        quarantine_port: QuarantinePort,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        pipeline_metrics: PipelineMetricsRecorder | None = None,
        batch_metrics: BatchMetricsRecorderService | None = None,
        run_type: str = "unknown",
        domain_event_emitter: DomainEventEmitterProtocol | None = None,
    ) -> None:
        """Initialize QuarantineRuntimeService with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.
            metrics: Optional metrics port for incrementing quarantine record
                counters per pipeline and error reason.
            pipeline_metrics: Optional prebuilt pipeline-scoped metrics recorder.
            batch_metrics: Optional run-type-aware recorder shared with batch processing.
            run_type: Run type label used by fallback direct metric emissions.

        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name
        self._metrics = metrics
        self._batch_metrics = batch_metrics
        self._run_type = run_type
        resolved_pipeline_metrics = pipeline_metrics
        if resolved_pipeline_metrics is None:
            resolved_pipeline_metrics = PipelineMetricsRecorder(
                metrics,
                pipeline_name,
            )
        self._pipeline_metrics = resolved_pipeline_metrics
        self._domain_event_emitter = domain_event_emitter

    async def quarantine_record(
        self,
        record: JsonDict,  # Any: quarantine record has heterogeneous values
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
        run_id: RunID | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write a record to the quarantine.

        Args:
            record: The raw record that failed processing.
            error_type: Classification of the error.
            batch_id: ID of the batch containing this record.
            error_details: Human-readable error description.
            run_id: Optional pipeline run identifier for traceability.
            ingestion_ts: Ingestion timestamp from context
                         (single source of time per ADR-014). Required.

        """
        request = build_dq_quarantine_request(
            pipeline_name=self._pipeline_name,
            record=record,
            error_type=error_type,
            error_details=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        await write_quarantine_request_with_events(
            quarantine=self._quarantine,
            request=request,
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            error_code=error_type.value,
            error_message=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        track_quarantine_metrics(
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            batch_metrics=self._batch_metrics,
            pipeline_name=self._pipeline_name,
            run_type=self._run_type,
            error_type=error_type,
            count=1,
        )
        track_processed_quarantined(
            metrics=self._metrics,
            batch_metrics=self._batch_metrics,
            pipeline_name=self._pipeline_name,
            run_type=self._run_type,
            count=1,
        )

    async def quarantine_records(
        self,
        records: list[DQQuarantineEntry],
        batch_id: BatchID,
        run_id: RunID | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write multiple data-quality records to quarantine in one call."""
        if not records:
            return

        write_requests = [
            build_dq_quarantine_request(
                pipeline_name=self._pipeline_name,
                record=record,
                error_type=error_type,
                error_details=error_details,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
            )
            for record, error_type, error_details in records
        ]
        await write_quarantine_requests_with_events(
            quarantine=self._quarantine,
            requests=write_requests,
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            error_codes=tuple(error_type.value for _, error_type, _ in records),
            error_messages=tuple(error_details for _, _, error_details in records),
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        for reason, count in count_dq_error_types(records).items():
            track_quarantine_metrics(
                metrics=self._metrics,
                pipeline_metrics=self._pipeline_metrics,
                batch_metrics=self._batch_metrics,
                pipeline_name=self._pipeline_name,
                run_type=self._run_type,
                error_type=reason,
                count=count,
            )


__all__ = [
    "DQQuarantineEntry",
    "FilteredQuarantineEntry",
    "QuarantineRuntimeService",
]
