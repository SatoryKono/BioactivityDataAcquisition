"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypeAlias

from bioetl.domain.ports import MetricsPort, QuarantinePort
from bioetl.domain.types import BatchID, ErrorType, JsonDict

_DQQuarantineEntry: TypeAlias = tuple[JsonDict, ErrorType, str]
_FilteredQuarantineEntry: TypeAlias = tuple[JsonDict, str]


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
        records: list[_DQQuarantineEntry],
        batch_id: BatchID,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write multiple data-quality records to quarantine in one call."""
        if not records:
            return

        write_requests = [
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
        ingestion_ts: datetime,
    ) -> None:
        """Write filter-excluded record to quasi-quarantine for traceability.

        These records are excluded by Silver filters (expected business rules),
        not by data-quality exceptions.

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
            metadata={
                "error_details": {"message": error_details},
                "quasi_quarantine": True,
                "classification": "filtered_out",
            },
            ingestion_ts=ingestion_ts,
        )
        if self._metrics:
            self._metrics.inc_quarantine_records(
                pipeline=self._pipeline_name,
                reason=error_code,
            )

    async def quarantine_filtered_records(
        self,
        records: list[_FilteredQuarantineEntry],
        batch_id: BatchID,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write multiple filter-excluded records to quasi-quarantine."""
        if not records:
            return

        error_code = "FILTERED_OUT_SILVER"
        write_requests = [
            {
                "pipeline": self._pipeline_name,
                "error_code": error_code,
                "payload": record,
                "bronze_batch_id": batch_id,
                "metadata": {
                    "error_details": {"message": error_details},
                    "quasi_quarantine": True,
                    "classification": "filtered_out",
                },
                "ingestion_ts": ingestion_ts,
            }
            for record, error_details in records
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

__all__ = ["QuarantineManager", "QuarantineManagerService"]
