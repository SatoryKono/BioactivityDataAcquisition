"""Quarantine service for administrative operations (Application layer).

Provides high-level quarantine management for CLI and other interfaces.
Uses QuarantinePort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

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


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Result of replaying quarantined records.

    Attributes:
        batch_id: Batch ID that was replayed.
        records_replayed: Number of records attempted to replay.
        records_succeeded: Number of successful replays.
        records_failed: Number of failed replays.
    """

    batch_id: str
    records_replayed: int
    records_succeeded: int
    records_failed: int


@dataclass(frozen=True, slots=True)
class PurgeResult:
    """Result of purging old quarantine records.

    Attributes:
        records_purged: Number of records removed.
        pipelines_affected: Pipelines that had records removed.
    """

    records_purged: int
    pipelines_affected: list[str]


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
        ...     print(f"{rec.error_code}: {rec.payload}")
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

    async def replay(
        self,
        pipeline: str,
        batch_id: UUID,
    ) -> ReplayResult:
        """Replay quarantined records from a specific batch.

        This operation attempts to reprocess records that were
        previously quarantined. The exact replay mechanism depends
        on the pipeline configuration and error type.

        Note: This is a placeholder for future implementation.
        Full replay requires pipeline context and transformation logic.

        Args:
            pipeline: Pipeline name.
            batch_id: Batch ID to replay.

        Returns:
            ReplayResult with replay statistics.
        """
        self.logger.info(
            "Replaying quarantine batch",
            pipeline=pipeline,
            batch_id=str(batch_id),
        )

        # Get records for this batch
        records = await self.quarantine_port.inspect(
            pipeline=pipeline,
            limit=10000,  # Large limit to get all batch records
        )

        # Filter to specific batch
        batch_records = [
            rec for rec in records
            if rec.get("bronze_batch_id") == str(batch_id)
        ]

        # Placeholder: actual replay would require pipeline context
        # For now, just return stats about what would be replayed
        self.logger.warning(
            "Replay not yet implemented - returning stats only",
            pipeline=pipeline,
            batch_id=str(batch_id),
            records_found=len(batch_records),
        )

        return ReplayResult(
            batch_id=str(batch_id),
            records_replayed=len(batch_records),
            records_succeeded=0,
            records_failed=len(batch_records),
        )

    async def purge(
        self,
        pipeline: str,
        older_than_days: int = 30,
    ) -> PurgeResult:
        """Purge old quarantine records.

        Removes quarantine records older than the specified age.
        This is a cleanup operation for maintaining quarantine storage.

        Note: This operation requires QuarantinePort to support
        time-based deletion, which may need to be implemented.

        Args:
            pipeline: Pipeline name (or "*" for all pipelines).
            older_than_days: Records older than this will be purged.

        Returns:
            PurgeResult with purge statistics.
        """
        self.logger.info(
            "Purging old quarantine records",
            pipeline=pipeline,
            older_than_days=older_than_days,
        )

        cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

        # Placeholder: actual purge requires QuarantinePort extension
        # For now, inspect and count what would be purged
        records = await self.quarantine_port.inspect(
            pipeline=pipeline,
            limit=10000,
        )

        # Filter by date (if ingestion_ts is available)
        records_to_purge = [
            rec for rec in records
            if rec.get("ingestion_ts") and rec["ingestion_ts"] < cutoff_date
        ]

        self.logger.warning(
            "Purge not yet implemented - returning stats only",
            pipeline=pipeline,
            older_than_days=older_than_days,
            records_found=len(records_to_purge),
        )

        return PurgeResult(
            records_purged=0,  # Not implemented yet
            pipelines_affected=[pipeline] if records_to_purge else [],
        )

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.quarantine_port.aclose()
