"""Quarantine service for administrative operations (Application layer).

Provides high-level quarantine management for CLI and other interfaces.
Uses QuarantinePort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import QuarantineRecordStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, QuarantinePort


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Representation of a quarantined record.

    Attributes:
        error_code: Error code that caused quarantine.
        payload: Original record data.
        batch_id: Bronze batch ID.
        pipeline: Pipeline name.
        ingestion_ts: When record was quarantined.
        metadata: Additional metadata.
    """

    error_code: str
    payload: dict[str, Any]
    batch_id: str | None
    pipeline: str
    ingestion_ts: datetime | None
    metadata: dict[str, Any]


@dataclass
class QuarantineService:
    """Service for administrative quarantine operations.

    Provides high-level operations for quarantine management
    used by CLI and other interfaces. Wraps QuarantinePort
    for Application-layer abstraction.

    Attributes:
        quarantine_port: Port for quarantine persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = QuarantineService(quarantine_port=port, logger=logger)
        >>> records = await service.inspect("chembl_activity", limit=10)
        >>> for rec in records:
        ...     logger.info("quarantine_record", error_code=rec.error_code, payload=rec.payload)
    """

    quarantine_port: QuarantinePort
    logger: LoggerPort

    async def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[QuarantineRecord]:
        """Inspect quarantined records for a pipeline.

        Args:
            pipeline: Pipeline name to inspect.
            limit: Maximum number of records to return.
            error_code: Optional filter by error code.

        Returns:
            List of QuarantineRecord objects.
        """
        self.logger.debug(
            "Inspecting quarantine",
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
        )

        raw_records = await self.quarantine_port.inspect(
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
        )

        records = [
            QuarantineRecord(
                error_code=rec.get("error_code", "UNKNOWN"),
                payload=rec.get("payload", {}),
                batch_id=rec.get("bronze_batch_id"),
                pipeline=pipeline,
                ingestion_ts=rec.get("ingestion_ts"),
                metadata=rec.get("metadata", {}),
            )
            for rec in raw_records
        ]

        self.logger.info(
            "Inspected quarantine",
            pipeline=pipeline,
            record_count=len(records),
        )

        return records

    async def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get statistics about quarantined records.

        Args:
            pipeline: Pipeline name.

        Returns:
            Dictionary with quarantine statistics by error code.
        """
        self.logger.debug("Getting quarantine stats", pipeline=pipeline)

        stats = await self.quarantine_port.get_stats(pipeline)

        self.logger.info(
            "Got quarantine stats",
            pipeline=pipeline,
            stats=stats,
        )

        return stats

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Replay quarantine records for reprocessing.

        Retrieves quarantined records that match the filter criteria
        for reprocessing by the pipeline.

        Args:
            pipeline: Pipeline name to filter by.
            error_code: Optional error code to filter by.
            max_age_days: Maximum age of records to replay (default 7).

        Returns:
            List of quarantine records suitable for replay.
        """
        now = datetime.now(tz=UTC)
        self.logger.info(
            "Replaying quarantine records",
            pipeline=pipeline,
            error_code=error_code,
            max_age_days=max_age_days,
        )

        records = list(
            self.quarantine_port.replay(
                pipeline=pipeline,
                error_code=error_code,
                max_age_days=max_age_days,
                now=now,
            )
        )

        self.logger.info(
            "Replay records retrieved",
            pipeline=pipeline,
            record_count=len(records),
        )

        return records

    def mark_as_reprocessed(
        self,
        records: list[dict[str, Any]],
    ) -> int:
        """Mark replay records as reprocessed.

        Updates the status of records to REPROCESSED after successful replay.

        Args:
            records: List of records from replay() to mark as reprocessed.

        Returns:
            Number of records successfully marked.
        """
        count = 0
        for rec in records:
            payload_hash = rec.get("payload_hash")
            if payload_hash and self.quarantine_port.update_status(
                payload_hash, QuarantineRecordStatus.REPROCESSED
            ):
                count += 1

        self.logger.info(
            "Marked records as reprocessed",
            record_count=count,
        )
        return count

    def purge(
        self,
        pipeline: str,
        older_than_days: int = 30,
    ) -> int:
        """Purge old quarantine records.

        Removes quarantine records older than the specified age.
        Implements RULES.md §2.6 - 30-day retention policy.

        Args:
            pipeline: Pipeline name.
            older_than_days: Records older than this will be purged (default 30).

        Returns:
            Number of records deleted.
        """
        now = datetime.now(tz=UTC)
        self.logger.info(
            "Purging old quarantine records",
            pipeline=pipeline,
            older_than_days=older_than_days,
        )

        count = self.quarantine_port.purge(
            pipeline=pipeline,
            older_than_days=older_than_days,
            now=now,
        )

        self.logger.info(
            "Purged quarantine records",
            pipeline=pipeline,
            records_purged=count,
        )

        return count

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
        self.logger.debug(
            "Updating quarantine status",
            payload_hash=payload_hash,
            new_status=new_status.value,
        )

        success = self.quarantine_port.update_status(payload_hash, new_status)

        if success:
            self.logger.info(
                "Updated quarantine status",
                payload_hash=payload_hash,
                new_status=new_status.value,
            )
        else:
            self.logger.warning(
                "Failed to update quarantine status - record not found",
                payload_hash=payload_hash,
            )

        return success

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.quarantine_port.aclose()
