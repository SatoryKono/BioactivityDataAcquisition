"""Delta table retention and maintenance facade."""

from __future__ import annotations

__all__ = ["RetentionPolicy"]

import asyncio
from typing import TYPE_CHECKING, Any

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import TableNotFoundError
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.settings_api import get_settings
from bioetl.infrastructure.storage.support.retention_dedup import (
    DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS,
    TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS,
    content_identity,
    deduplicate_delta_rows,
)
from bioetl.infrastructure.storage.support.retention_delta import (
    build_table_info,
    get_table_path,
)
from bioetl.infrastructure.storage.support.retention_time_travel import (
    load_time_travel_table,
)

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

_content_identity = content_identity


def _resolve_deduplication_timeout_seconds() -> float:
    settings = get_settings()
    configured = float(
        getattr(
            settings,
            "silver_dedup_timeout_seconds",
            DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS,
        )
    )
    if (
        getattr(settings, "test_mode", False)
        and configured >= DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS
    ):
        return TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
    return configured


def _load_delta_table(table_path: str) -> DeltaTable:
    """Load a Delta table through the retention module patch seam."""
    try:
        return DeltaTable(table_path)
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc


class RetentionPolicy:
    """Manager for Delta table retention and maintenance operations."""

    def __init__(
        self,
        base_path: str | Path,
        *,
        deduplicate_timeout_seconds: float | None = None,
    ) -> None:
        """Initialize retention manager."""
        self.base_path = str(base_path).rstrip("/")
        timeout = (
            deduplicate_timeout_seconds
            if deduplicate_timeout_seconds is not None
            else _resolve_deduplication_timeout_seconds()
        )
        self._deduplicate_timeout_seconds = (
            timeout if timeout > 0 else DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS
        )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files that are no longer referenced by the Delta log."""
        table_path = get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()
        dt = await loop.run_in_executor(None, lambda: _load_delta_table(table_path))
        return await loop.run_in_executor(
            None,
            lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
        )

    async def optimize(
        self,
        table_name: str,
        target_size: int | None = None,
        partition_filters: (
            list[
                tuple[str, str, Any]  # Any: Delta Lake partition filter values vary
            ]  # Any: Delta Lake partition filter values vary
            | None
        ) = None,  # Any: Delta Lake filter value type varies
    ) -> JsonDict:  # Any: compaction result metrics
        """Optimize table layout through file compaction.

        Compacts small files into larger ones for better query performance.

        Args:
            table_name: Table name.
            target_size: Target file size in bytes (currently unused, reserved for future
                        delta-rs API support).
            partition_filters: Optional filters to limit optimization to specific partitions.
                List of tuples with format [(column, op, value), ...],
                e.g., [("date", "=", "2024-01-01")].

        Returns:
            Optimization metrics dictionary with details about files processed.

        Raises:
            TableNotFoundError: If table does not exist.
        """
        # Note: target_size reserved for future delta-rs API support
        _ = target_size  # Suppress unused variable warning
        table_path = get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()
        filters = partition_filters  # Capture for lambda closure
        dt = await loop.run_in_executor(None, lambda: _load_delta_table(table_path))
        return await loop.run_in_executor(
            None, lambda: dt.optimize.compact(partition_filters=filters)
        )

    async def get_table_info(
        self, table_name: str
    ) -> JsonDict:  # Any: record/metadata values are heterogeneous
        """Get metadata about a Delta table.

        Args:
            table_name: Table name.

        Returns:
            Dictionary with table metadata:
            - version: Current table version number
            - num_files: Number of data files
            - schema: PyArrow schema of the table
            - metadata: Table metadata dictionary

        Raises:
            TableNotFoundError: If table does not exist.
        """
        table_path = get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()
        dt = await loop.run_in_executor(None, lambda: _load_delta_table(table_path))
        return build_table_info(dt)

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int:
        """Deduplicate Silver table by primary keys using deterministic content identity.

        The compaction contract is intentionally content-aware:
        - exact duplicate rows for one business key collapse by
          ``(primary_keys, content identity)``
        - conflicting rows for one business key choose a deterministic winner
          by the lexicographically smallest content identity

        This avoids relying on runtime ingestion timestamps, which would make
        replay and publication semantics depend on occurrence metadata rather than
        persisted content.

        Args:
            table_name: Table name (e.g., 'chembl/activity').
            primary_keys: Columns forming the business key for dedup.

        Returns:
            Number of duplicate rows removed.

        Raises:
            TableNotFoundError: If table does not exist.
        """
        table_path = get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()
        try:
            result: int = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: deduplicate_delta_rows(table_path, primary_keys),
                ),
                timeout=self._deduplicate_timeout_seconds,
            )
        except TimeoutError as exc:
            raise TimeoutError(
                "Silver deduplication timed out "
                f"after {self._deduplicate_timeout_seconds:.1f}s "
                f"for table '{table_name}'"
            ) from exc
        return result

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Read table snapshot at a specific version or timestamp.

        Args:
            table_name: Delta table name (relative to base path).
            version: Specific table version number to load.
            timestamp: Point-in-time datetime for time travel.

        Returns:
            DeltaTable instance at the requested snapshot.

        Raises:
            ValueError: If both or neither version/timestamp are specified.
            TableNotFoundError: If the Delta table does not exist.

        Note:
            The timestamp branch uses ``storage_options`` to pass the
            timestamp — verify compatibility with your delta-rs version.
            Version-based time travel is the more reliable path.
        """
        return await load_time_travel_table(
            base_path=self.base_path,
            table_name=table_name,
            version=version,
            timestamp=timestamp,
            delta_table_factory=DeltaTable,
        )
