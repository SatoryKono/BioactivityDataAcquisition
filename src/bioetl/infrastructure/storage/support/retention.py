"""Delta table retention and maintenance operations.

Implements RULES.md §2.1.1 - Delta Lake specifications:
- REQ-DELTA-002: VACUUM scheduler (7-day retention)
- REQ-DELTA-003: Forensic retention (7-30 days configurable)
- REQ-DATA-008: Time Travel support

This module extracts maintenance operations from SilverWriter for better
separation of concerns:
- VACUUM: Remove old files no longer referenced by Delta log
- Optimize: Compact files for better query performance
- Time Travel: Read historical versions of tables
- Table Info: Retrieve metadata about Delta tables
"""

from __future__ import annotations

__all__ = ["RetentionPolicy"]

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from deltalake import DeltaTable
from deltalake.exceptions import CommitFailedError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import DeltaWriteConflictError, TableNotFoundError
from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.settings_api import get_settings

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

_DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS = 60.0
_TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS = 10.0


def _resolve_deduplication_timeout_seconds() -> float:
    """Return the centralized dedup timeout setting with a safe fallback."""
    settings = get_settings()
    configured_timeout = float(
        getattr(
            settings,
            "silver_dedup_timeout_seconds",
            _DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS,
        )
    )
    if (
        getattr(settings, "test_mode", False)
        and configured_timeout >= _DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS
    ):
        return _TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
    return configured_timeout


def _primary_key_tuple(
    row: JsonDict,
    primary_keys: Sequence[str],
) -> tuple[object, ...]:
    """Return one stable primary-key tuple for a Delta row."""
    return tuple(row.get(key) for key in primary_keys)


def _content_identity(row: JsonDict) -> str:
    """Return deterministic content identity for one Delta row."""
    content_hash = row.get("content_hash")
    if content_hash is not None:
        return str(content_hash)
    return serialize_hash_identity_canonical_json(normalize_hash_identity_record(row))


def _get_table_path(base_path: str, table_name: str) -> str:
    """Get the filesystem path for a table."""
    return f"{base_path}/{table_name.replace('.', '/')}"


def _load_delta_table(table_path: str) -> DeltaTable:
    """Load a Delta table or translate the not-found error to the domain type."""
    try:
        return DeltaTable(table_path)
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc


def _build_table_info(table: DeltaTable) -> JsonDict:
    """Build the normalized table-info payload from an open Delta table."""
    return {
        "version": table.version(),
        "num_files": len(table.file_uris()),
        "schema": table.schema().to_arrow(),
        "metadata": table.metadata(),
    }


def _deduplicate_delta_rows(
    table_path: str,
    primary_keys: Sequence[str],
) -> int:
    """Deduplicate one Delta table using deterministic content identity."""
    import pyarrow as pa
    from deltalake import DeltaTable as runtime_delta_table
    from deltalake import write_deltalake

    try:
        table = runtime_delta_table(table_path).to_pyarrow_table()
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc
    total_before = table.num_rows
    if total_before == 0:
        return 0

    ranked_rows = sorted(
        (
            (
                _primary_key_tuple(row, primary_keys),
                _content_identity(row),
                row,
            )
            for row in table.to_pylist()
        ),
        key=lambda item: (item[0], item[1]),
    )

    seen_exact_keys: set[tuple[tuple[object, ...], str]] = set()
    seen_primary_keys: set[tuple[object, ...]] = set()
    deduped_rows: list[JsonDict] = []
    for primary_key, content_identity, row in ranked_rows:
        exact_key = (primary_key, content_identity)
        if exact_key in seen_exact_keys:
            continue
        seen_exact_keys.add(exact_key)
        if primary_key in seen_primary_keys:
            continue
        seen_primary_keys.add(primary_key)
        deduped_rows.append(row)

    duplicates_removed = total_before - len(deduped_rows)
    if duplicates_removed > 0:
        try:
            write_deltalake(
                table_or_uri=table_path,
                data=pa.Table.from_pylist(deduped_rows, schema=table.schema),
                mode="overwrite",
                schema_mode="overwrite",
            )
        except CommitFailedError as exc:
            raise DeltaWriteConflictError(
                table_path=table_path,
                operation="deduplicate",
            ) from exc
    return int(duplicates_removed)


class RetentionPolicy:
    """Manager for Delta table retention and maintenance operations.

    Handles VACUUM, optimize, time travel, and table metadata retrieval.
    Extracted from SilverWriter to improve separation of concerns.
    """

    def __init__(
        self,
        base_path: str | Path,
        *,
        deduplicate_timeout_seconds: float | None = None,
    ) -> None:
        """Initialize retention manager.

        Args:
            base_path: Base path for Delta tables (local filesystem).
            deduplicate_timeout_seconds:
                Maximum time budget for silver deduplication executor work.
                Falls back to centralized settings, then to a safe default.
        """
        self.base_path = str(base_path).rstrip("/")
        timeout = (
            deduplicate_timeout_seconds
            if deduplicate_timeout_seconds is not None
            else _resolve_deduplication_timeout_seconds()
        )
        self._deduplicate_timeout_seconds = (
            timeout if timeout > 0 else _DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS
        )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files that are no longer referenced by the Delta log.

        Implements REQ-DELTA-002 and REQ-DELTA-003.

        Args:
            table_name: Table name.
            retention_hours: Hours of retention (default uses Delta Lake default of 168 hours).
                            Must be >= 168 hours unless explicitly overridden at table level.
            dry_run: If True, only list files to be deleted without deleting them.

        Returns:
            List of files deleted (or to be deleted in dry_run mode).

        Raises:
            TableNotFoundError: If table does not exist.
        """
        table_path = _get_table_path(self.base_path, table_name)
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
        table_path = _get_table_path(self.base_path, table_name)
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
        table_path = _get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()
        dt = await loop.run_in_executor(None, lambda: _load_delta_table(table_path))
        return _build_table_info(dt)

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
        table_path = _get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()
        try:
            result: int = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: _deduplicate_delta_rows(table_path, primary_keys),
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
        if version is not None and timestamp is not None:
            raise ValueError("Specify either version or timestamp, not both")

        table_path = _get_table_path(self.base_path, table_name)
        loop = asyncio.get_running_loop()

        try:
            if version is not None:
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        version=version,
                    ),
                )
            elif timestamp is not None:
                timestamp_str = timestamp.isoformat()
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        storage_options={
                            "time_travel": timestamp_str,
                        },
                    ),
                )
            else:
                raise ValueError("Must specify either version or timestamp")
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e
