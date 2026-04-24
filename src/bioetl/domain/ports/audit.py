"""Audit port for traceability of write operations.

Implements audit logging requirements for write operations across all
Medallion layers (Bronze, Silver, Gold).

Requirements:
- REQ-AUDIT-001: Each write operation must be logged
- REQ-AUDIT-002: Audit log must contain run_id, timestamp, records_count, table
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from bioetl.domain.types import JsonDict, MetaDict, RunID

__all__ = [
    "AuditEntry",
    "AuditLayer",
    "AuditOperation",
    "AuditPort",
]


class AuditOperation(StrEnum):
    """Types of auditable write operations."""

    WRITE = "write"
    """Standard write operation."""

    MERGE = "merge"
    """Upsert/merge operation."""

    APPEND = "append"
    """Append-only write."""

    DELETE = "delete"
    """Delete and replace operation."""

    OVERWRITE = "overwrite"
    """Full overwrite operation."""


class AuditLayer(StrEnum):
    """Medallion layers for audit tracking."""

    BRONZE = "bronze"
    """Raw data layer."""

    SILVER = "silver"
    """Normalized data layer."""

    GOLD = "gold"
    """Business-ready data layer."""


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Immutable audit log entry for write operations.

    Captures the "who, what, when, where" for each write operation
    to ensure full traceability across the data pipeline.

    Attributes:
        run_id: Pipeline run identifier for correlation.
        timestamp: When the operation occurred (UTC).
        layer: Medallion layer (bronze/silver/gold).
        table_name: Target table or path.
        operation: Type of write operation performed.
        records_count: Number of records written.
        metadata: Additional context (batch_id, provider, entity, etc.).
    """

    run_id: RunID
    timestamp: datetime
    layer: AuditLayer
    table_name: str
    operation: AuditOperation
    records_count: int
    metadata: MetaDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:  # Any: serialized repr mixes str/int/list
        """Convert entry to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "run_id": str(self.run_id),
            "timestamp": self.timestamp.isoformat(),
            "layer": self.layer.value,
            "table_name": self.table_name,
            "operation": self.operation.value,
            "records_count": self.records_count,
            "metadata": self.metadata,
        }


@runtime_checkable
class AuditPort(Protocol):
    """Port for audit logging of write operations.

    Abstracts the audit log storage mechanism, allowing different
    implementations (file, database, etc.) while maintaining a
    consistent interface for the storage writers.

    Note: AuditPort uses async methods since audit operations may
    involve I/O (writing to files or external systems).
    """

    async def log_write(self, entry: AuditEntry) -> None:
        """Log a write operation to the audit trail.

        Args:
            entry: The audit entry containing operation details.

        Raises:
            AuditError: If the audit log write fails.
        """
        ...

    async def get_entries(
        self,
        run_id: RunID | None = None,
        layer: AuditLayer | None = None,
        table_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters.

        Args:
            run_id: Filter by pipeline run ID.
            layer: Filter by Medallion layer.
            table_name: Filter by target table name.
            start_time: Filter entries after this time.
            end_time: Filter entries before this time.
            limit: Maximum number of entries to return.

        Returns:
            List of matching audit entries, ordered by timestamp descending.
        """
        ...

    def log_event(
        self,
        event_name: str,
        event_data: JsonDict | None = None,
        *,
        timestamp: datetime,
    ) -> None:
        """Log a non-write audit event to the audit trail.

        Args:
            event_name: Stable event name for the audited lifecycle event.
            event_data: Optional structured event context.
            timestamp: Canonical event timestamp supplied by the caller.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the audit log and release resources.

        This method should be called when the pipeline is shutting down
        to ensure all audit entries are flushed. The implementation
        MUST be idempotent (safe to call multiple times).
        """
        ...
