"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-0005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bioetl.domain.ports import QuarantinePort
from bioetl.domain.types import BatchID, ErrorType


class QuarantineManager:
    """Manages quarantining of records that fail processing.

    This manager handles writing failed records to quarantine storage
    for later analysis and potential reprocessing.
    """

    def __init__(
        self,
        quarantine_port: QuarantinePort,
        pipeline_name: str,
    ) -> None:
        """Initialize QuarantineManager with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.

        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name

    async def quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
        ingestion_ts: datetime | None = None,
    ) -> None:
        """Write a record to the quarantine.

        Args:
            record: The raw record that failed processing.
            error_type: Classification of the error.
            batch_id: ID of the batch containing this record.
            error_details: Human-readable error description.
            ingestion_ts: Ingestion timestamp from context (single source of time).

        """
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            metadata={"error_details": {"message": error_details}},
            ingestion_ts=ingestion_ts,
        )

    async def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]:
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

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about quarantined records for this pipeline.

        Delegates to QuarantinePort.get_stats() for CLI reporting.

        Returns:
            Dictionary with quarantine statistics.

        """
        return await self._quarantine.get_stats(self._pipeline_name)
