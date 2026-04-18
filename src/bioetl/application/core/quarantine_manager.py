"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from bioetl.application.observability.domain_event_emitter import DomainEventEmitterPort
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.aggregates.events import RecordQuarantined
from bioetl.domain.aggregates.quarantine_entry import QuarantineEntry
from bioetl.domain.ports import MetricsPort, QuarantinePort, QuarantineWriteRequest
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


def _filtered_quarantine_metadata(
    *,
    reason: str,
    details: JsonDict | None,
) -> JsonDict:
    """Build canonical quarantine metadata for Silver filter rejections.

    The human-readable ``reason`` is stored as display text under ``message``.
    Structured fields in ``details`` remain the stable analytical contract for
    grouping and drilldown. Callers cannot override ``message`` through
    ``details``.
    """
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

    def _track_quarantine_metrics(self, error_type: ErrorType, count: int) -> None:
        """Emit quarantine metrics through both legacy and current metric APIs."""
        if self._metrics is None:
            return

        track_quarantined_records = getattr(
            self._metrics, "track_quarantined_records", None
        )
        if callable(track_quarantined_records):
            track_quarantined_records(error_type, count)

        self._metrics.increment_counter(
            "bioetl_dq_records_quarantined_total",
            count,
            {"pipeline": self._pipeline_name, "error_type": error_type.value},
        )
        self._pipeline_metrics.record_quarantine_records(
            reason=error_type.value,
            count=count,
        )

    def _track_processed_quarantined(self, count: int) -> None:
        """Emit processed-record metrics for the quarantine stage."""
        if self._metrics is None:
            return

        track_processed_records = getattr(
            self._metrics, "track_processed_records", None
        )
        if callable(track_processed_records):
            track_processed_records("quarantined", count)

        self._metrics.increment_counter(
            "bioetl_records_processed_total",
            count,
            {"pipeline": self._pipeline_name, "stage": "quarantined"},
        )

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
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            run_id=run_id,
            metadata={"error_details": {"message": error_details}},
            ingestion_ts=ingestion_ts,
        )
        self._emit_quarantine_events(
            payload=record,
            error_code=error_type.value,
            error_message=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
            metadata={"error_details": {"message": error_details}},
        )
        self._track_quarantine_metrics(error_type, 1)
        self._track_processed_quarantined(1)

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

        write_requests: list[QuarantineWriteRequest] = [
            {
                "pipeline": self._pipeline_name,
                "error_code": error_type.value,
                "payload": record,
                "bronze_batch_id": batch_id,
                "run_id": run_id,
                "metadata": {"error_details": {"message": error_details}},
                "ingestion_ts": ingestion_ts,
            }
            for record, error_type, error_details in records
        ]
        await self._quarantine.write_many(write_requests)
        for request, (_, error_type, error_details) in zip(
            write_requests, records, strict=True
        ):
            self._emit_quarantine_events(
                payload=request["payload"],
                error_code=error_type.value,
                error_message=error_details,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
                metadata=request["metadata"],
            )
        if self._metrics:
            counts_by_reason: dict[ErrorType, int] = {}
            for _, error_type, _ in records:
                counts_by_reason[error_type] = counts_by_reason.get(error_type, 0) + 1
            for reason, count in counts_by_reason.items():
                self._track_quarantine_metrics(reason, count)

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
        error_code = "FILTERED_OUT_SILVER"
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_code,
            payload=record,
            bronze_batch_id=batch_id,
            run_id=run_id,
            metadata=_filtered_quarantine_metadata(
                reason=error_details,
                details=details,
            ),
            ingestion_ts=ingestion_ts,
        )
        self._emit_quarantine_events(
            payload=record,
            error_code=error_code,
            error_message=error_details,
            batch_id=batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
            metadata=_filtered_quarantine_metadata(
                reason=error_details,
                details=details,
            ),
        )
        if self._metrics:
            self._pipeline_metrics.record_quarantine_records(
                reason=error_code,
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

        error_code = "FILTERED_OUT_SILVER"
        write_requests: list[QuarantineWriteRequest] = [
            {
                "pipeline": self._pipeline_name,
                "error_code": error_code,
                "payload": entry.record,
                "bronze_batch_id": batch_id,
                "run_id": run_id,
                "metadata": _filtered_quarantine_metadata(
                    reason=entry.reason,
                    details=entry.details,
                ),
                "ingestion_ts": ingestion_ts,
            }
            for entry in records
        ]
        await self._quarantine.write_many(write_requests)
        for request, entry in zip(write_requests, records, strict=True):
            self._emit_quarantine_events(
                payload=request["payload"],
                error_code=error_code,
                error_message=entry.reason,
                batch_id=batch_id,
                run_id=run_id,
                ingestion_ts=ingestion_ts,
                metadata=request["metadata"],
            )
        if self._metrics:
            self._pipeline_metrics.record_quarantine_records(
                reason=error_code,
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

    def _emit_quarantine_events(
        self,
        *,
        payload: BronzeRecord,
        error_code: str,
        error_message: str,
        batch_id: BatchID,
        run_id: RunID | None,
        ingestion_ts: datetime,
        metadata: JsonDict | None,
    ) -> None:
        """Publish typed quarantine events when stable correlation IDs are present."""
        if self._domain_event_emitter is None or run_id is None:
            return

        entry = QuarantineEntry.create(
            pipeline_name=self._pipeline_name,
            error_code=error_code,
            payload=payload,
            run_id=run_id,
            batch_id=batch_id,
            created_at=ingestion_ts,
            metadata=metadata,
        )
        for event in entry.collect_events():
            self._domain_event_emitter.emit_domain_event(event)

        self._domain_event_emitter.emit_domain_event(
            RecordQuarantined(
                occurred_at=ingestion_ts,
                run_id=run_id,
                batch_id=batch_id,
                record_id=self._extract_record_id(payload),
                error_code=error_code,
                error_message=error_message,
                content_hash=entry.payload_hash,
            )
        )

    @staticmethod
    def _extract_record_id(payload: BronzeRecord) -> str | None:
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


__all__ = [
    "DQQuarantineEntry",
    "FilteredQuarantineEntry",
    "QuarantineManager",
    "QuarantineManagerService",
]

# Backward-compatible public alias for historical call sites and tests.
QuarantineManager = QuarantineManagerService
