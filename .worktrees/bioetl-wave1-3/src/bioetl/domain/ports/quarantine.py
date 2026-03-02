"""Quarantine port for isolating failed records.

This port provides a way to isolate records that fail processing
for later analysis, preventing them from stopping the entire pipeline.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from bioetl.domain.types import BatchID, QuarantineRecordStatus, RunID


@runtime_checkable
class QuarantinePort(Protocol):
    """Port for quarantining failed records.

    This interface provides a way to isolate records that fail processing
    for later analysis, preventing them from stopping the entire pipeline.
    """

    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        run_id: RunID | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        ingestion_ts: datetime,
    ) -> None:
        """Write a record to quarantine.

        Args:
            pipeline: The name of the pipeline where the error occurred.
            error_code: A code identifying the type of error.
            payload: The record that failed processing.
            bronze_batch_id: The ID of the bronze batch containing the record.
            run_id: Optional ID of the pipeline run for traceability.
            metadata: Optional additional metadata (e.g., error_details, bronze_file_uri).
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.
        """
        ...

    async def inspect(
        self,
        pipeline: str,
        limit: int = 10,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect records in quarantine.

        Args:
            pipeline: The name of the pipeline to inspect.
            limit: The maximum number of records to return.
            error_code: Filter records by a specific error code.

        Returns:
            A list of quarantined records.
        """
        ...

    async def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get statistics about the quarantined records for a pipeline.

        Args:
            pipeline: The name of the pipeline.

        Returns:
            A dictionary of statistics (e.g., count by error code).
        """
        ...

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
        *,
        now: datetime,
    ) -> Iterator[dict[str, Any]]:
        """Replay quarantine records for reprocessing.

        Retrieves quarantined records that match the filter criteria
        for reprocessing by the pipeline.

        Args:
            pipeline: Pipeline name to filter by.
            error_code: Optional error code to filter by.
            max_age_days: Maximum age of records to replay (default 7).
            now: Current timestamp from application layer
                 (single source of time per ADR-014). Required.

        Returns:
            Iterator of quarantine records suitable for replay.
        """
        ...

    def purge(
        self,
        pipeline: str,
        older_than_days: int = 30,
        *,
        now: datetime,
    ) -> int:
        """Purge old quarantine records.

        Deletes quarantined records older than the specified age.
        Implements RULES.md §2.6 - 30-day retention policy.

        Args:
            pipeline: Pipeline name to filter by.
            older_than_days: Delete records older than this (default 30).
            now: Current timestamp from application layer
                 (single source of time per ADR-014). Required.

        Returns:
            Count of deleted records.
        """
        ...

    def update_status(
        self,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
    ) -> bool:
        """Update DQ status for a quarantined record.

        Used to mark records as IGNORED, REVIEWED, or REPROCESSED
        after manual inspection.

        Args:
            payload_hash: Hash of the payload to identify the record.
            new_status: New status to set.

        Returns:
            True if record was found and updated, False otherwise.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the quarantine connection and release resources."""
        ...
