"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from bioetl.application.core._quarantine_support import (
    FILTERED_OUT_SILVER,
    build_dq_quarantine_request,
    build_filtered_quarantine_request,
    count_dq_error_types,
    emit_quarantine_events,
    record_filtered_quarantine_metrics,
    track_processed_quarantined,
    track_quarantine_metrics,
)
from bioetl.application.observability.domain_event_emitter import DomainEventEmitterPort
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.ports import MetricsPort, QuarantinePort
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, JsonDict, RunID


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


class QuarantineManagerService:
    """Manages quarantining of records that fail processing.

    This manager handles writing failed records to quarantine storage
    for later analysis and potential reprocessing.
    """

    def __init__(
        self,
        quarantine_port: QuarantinePort,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        pipeline_metrics: PipelineMetricsRecorder | None = None,
        domain_event_emitter: DomainEventEmitterPort | None = None,
    ) -> None:
        """Initialize QuarantineManagerService with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.
            metrics: Optional metrics port for incrementing quarantine record
                counters per pipeline and error reason.
            pipeline_metrics: Optional prebuilt pipeline-scoped metrics recorder.

        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name
        self._metrics = metrics
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
        await self._quarantine.write(**request)
        emit_quarantine_events(
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            payload=record,
            error_code=error_type.value,
            error_message=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
            metadata=request["metadata"],
        )
        track_quarantine_metrics(
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            pipeline_name=self._pipeline_name,
            error_type=error_type,
            count=1,
        )
        track_processed_quarantined(
            metrics=self._metrics,
            pipeline_name=self._pipeline_name,
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
        await self._quarantine.write_many(write_requests)
        for request, (_, error_type, error_details) in zip(
            write_requests, records, strict=True
        ):
            emit_quarantine_events(
                emitter=self._domain_event_emitter,
                pipeline_name=self._pipeline_name,
                payload=request["payload"],
                error_code=error_type.value,
                error_message=error_details,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
                metadata=request["metadata"],
            )
        for reason, count in count_dq_error_types(records).items():
            track_quarantine_metrics(
                metrics=self._metrics,
                pipeline_metrics=self._pipeline_metrics,
                pipeline_name=self._pipeline_name,
                error_type=reason,
                count=count,
            )

    async def quarantine_filtered_record(
        self,
        record: JsonDict,  # Any: quarantine record has heterogeneous values
        batch_id: BatchID,
        error_details: str,
        run_id: RunID | None = None,
        *,
        details: JsonDict | None = None,
        ingestion_ts: datetime,
    ) -> None:
        """Write filter-excluded record to quarantine for traceability.

        These records are excluded by Silver filters (expected business rules),
        not by data-quality exceptions, so they use a separate classification.

        Args:
            record: The raw record excluded by Silver filters.
            batch_id: ID of the batch containing this record.
            error_details: Human-readable exclusion reason.
            run_id: Optional pipeline run identifier for traceability.
            ingestion_ts: Ingestion timestamp from context.
        """
        request = build_filtered_quarantine_request(
            pipeline_name=self._pipeline_name,
            record=record,
            reason=error_details,
            details=details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )
        await self._quarantine.write(**request)
        emit_quarantine_events(
            emitter=self._domain_event_emitter,
            pipeline_name=self._pipeline_name,
            payload=record,
            error_code=FILTERED_OUT_SILVER,
            error_message=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
            metadata=request["metadata"],
        )
        record_filtered_quarantine_metrics(
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            count=1,
        )

    async def quarantine_filtered_records(
        self,
        records: list[FilteredQuarantineEntry],
        batch_id: BatchID,
        run_id: RunID | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write multiple filter-excluded records to quarantine."""
        if not records:
            return

        write_requests = [
            build_filtered_quarantine_request(
                pipeline_name=self._pipeline_name,
                record=entry.record,
                reason=entry.reason,
                details=entry.details,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
            )
            for entry in records
        ]
        await self._quarantine.write_many(write_requests)
        for request, entry in zip(write_requests, records, strict=True):
            emit_quarantine_events(
                emitter=self._domain_event_emitter,
                pipeline_name=self._pipeline_name,
                payload=request["payload"],
                error_code=FILTERED_OUT_SILVER,
                error_message=entry.reason,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
                metadata=request["metadata"],
            )
        record_filtered_quarantine_metrics(
            metrics=self._metrics,
            pipeline_metrics=self._pipeline_metrics,
            count=len(records),
        )

    async def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> list[JsonDict]:  # Any: quarantine record has heterogeneous values
        """Inspect quarantined records for this pipeline.

        Delegates to QuarantinePort.inspect() for CLI inspection commands.

        Args:
            limit: Maximum number of records to return.
            error_code: Optional filter by error code.
            run_id: Optional filter by pipeline run ID.

        Returns:
            List of quarantined records.

        """
        records: list[JsonDict] = await self._quarantine.inspect(
            pipeline=self._pipeline_name,
            limit=limit,
            error_code=error_code,
            run_id=run_id,
        )
        return records

    async def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> JsonDict:  # Any: quarantine record has heterogeneous values
        """Get statistics about quarantined records for this pipeline.

        Delegates to QuarantinePort.get_stats() for CLI reporting.

        Args:
            error_code: Optional error code to scope the statistics.
            run_id: Optional pipeline run ID to scope the statistics.

        Returns:
            Dictionary with quarantine statistics.

        """
        return await self._quarantine.get_stats(
            self._pipeline_name,
            error_code,
            run_id,
        )


__all__ = [
    "DQQuarantineEntry",
    "FilteredQuarantineEntry",
    "QuarantineManager",
    "QuarantineManagerService",
]

# Backward-compatible public alias for historical call sites and tests.
QuarantineManager = QuarantineManagerService
