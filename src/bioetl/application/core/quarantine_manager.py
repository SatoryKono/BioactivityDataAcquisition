"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from bioetl.domain.ports import MetricsPort, QuarantinePort, QuarantineWriteRequest
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, JsonDict


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
    """Build canonical quarantine metadata for Silver filter rejections."""
    error_details: JsonDict = {"message": reason}
    if details:
        error_details.update(details)
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
    ) -> None:
        """Initialize QuarantineManager with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.
            metrics: Optional metrics port for incrementing quarantine record
                counters per pipeline and error reason.

        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name
        self._metrics = metrics

    async def quarantine_record(
        self,
        record: JsonDict,  # Any: quarantine record has heterogeneous values
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write a record to the quarantine.

        Args:
            record: The raw record that failed processing.
            error_type: Classification of the error.
            batch_id: ID of the batch containing this record.
            error_details: Human-readable error description.
            ingestion_ts: Ingestion timestamp from context
                         (single source of time per ADR-014). Required.

        """
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            metadata={"error_details": {"message": error_details}},
            ingestion_ts=ingestion_ts,
        )
        if self._metrics:
            self._metrics.inc_quarantine_records(
                pipeline=self._pipeline_name,
                reason=error_type.value,
            )

    async def quarantine_records(
        self,
        records: list[DQQuarantineEntry],
        batch_id: BatchID,
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
                "metadata": {"error_details": {"message": error_details}},
                "ingestion_ts": ingestion_ts,
            }
            for record, error_type, error_details in records
        ]
        await self._quarantine.write_many(write_requests)
        if self._metrics:
            counts_by_reason: dict[str, int] = {}
            for _, error_type, _ in records:
                counts_by_reason[error_type.value] = (
                    counts_by_reason.get(error_type.value, 0) + 1
                )
            for reason, count in counts_by_reason.items():
                self._metrics.inc_quarantine_records(
                    pipeline=self._pipeline_name,
                    reason=reason,
                    count=count,
                )

    async def quarantine_filtered_record(
        self,
        record: JsonDict,  # Any: quarantine record has heterogeneous values
        batch_id: BatchID,
        error_details: str,
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
            ingestion_ts: Ingestion timestamp from context.
        """
        error_code = "FILTERED_OUT_SILVER"
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_code,
            payload=record,
            bronze_batch_id=batch_id,
            metadata=_filtered_quarantine_metadata(
                reason=error_details,
                details=details,
            ),
            ingestion_ts=ingestion_ts,
        )
        if self._metrics:
            self._metrics.inc_quarantine_records(
                pipeline=self._pipeline_name,
                reason=error_code,
            )

    async def quarantine_filtered_records(
        self,
        records: list[FilteredQuarantineEntry],
        batch_id: BatchID,
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
                "metadata": _filtered_quarantine_metadata(
                    reason=entry.reason,
                    details=entry.details,
                ),
                "ingestion_ts": ingestion_ts,
            }
            for entry in records
        ]
        await self._quarantine.write_many(write_requests)
        if self._metrics:
            self._metrics.inc_quarantine_records(
                pipeline=self._pipeline_name,
                reason=error_code,
                count=len(records),
            )

    async def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[JsonDict]:  # Any: quarantine record has heterogeneous values
        """Inspect quarantined records for this pipeline.

        Delegates to QuarantinePort.inspect() for CLI inspection commands.

        Args:
            limit: Maximum number of records to return.
            error_code: Optional filter by error code.

        Returns:
            List of quarantined records.

        """
        return await self._quarantine.inspect(
            pipeline=self._pipeline_name,
            limit=limit,
            error_code=error_code,
        )

    async def get_stats(
        self,
    ) -> JsonDict:  # Any: quarantine record has heterogeneous values
        """Get statistics about quarantined records for this pipeline.

        Delegates to QuarantinePort.get_stats() for CLI reporting.

        Returns:
            Dictionary with quarantine statistics.

        """
        return await self._quarantine.get_stats(self._pipeline_name)


QuarantineManager = QuarantineManagerService

__all__ = [
    "DQQuarantineEntry",
    "FilteredQuarantineEntry",
    "QuarantineManager",
    "QuarantineManagerService",
]
