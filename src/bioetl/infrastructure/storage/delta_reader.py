"""Delta Lake reader for table access and export.

Provides read-only access to Silver/Gold Delta Lake tables
using delta-rs library.

Implements DeltaReaderPort for export utilities.
"""

from __future__ import annotations

__all__ = ["DeltaReader"]


import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class DeltaReader:
    """Read-only accessor for Delta Lake tables.

    Provides efficient reading with column projection and row limiting.
    Uses async wrappers around sync delta-rs operations.
    """

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
    ) -> None:
        """Initialize Delta reader.

        Args:
            base_path: Base path for Delta table storage.
                      Tables are read from subdirectories (e.g., base_path/chembl/activity/).
            logger: Structured logger for observability (MUST be injected).
        """
        self._base_path = Path(base_path)
        self._logger = logger

    def _resolve_path(self, table_path: str) -> Path:
        """Resolve table path to absolute path.

        Handles both relative paths (provider/entity) and absolute paths.

        Args:
            table_path: Table path, can be relative (chembl/activity) or absolute.

        Returns:
            Absolute Path to the table directory.
        """
        path = Path(table_path)
        if path.is_absolute():
            return path
        return self._base_path / table_path

    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read data from a Delta Lake table.

        Args:
            table_path: Path to the Delta table (relative or absolute).
            columns: Optional list of columns to read (projection pushdown).
            limit: Optional maximum number of rows to read.

        Returns:
            PyArrow Table with the requested data.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _read() -> pa.Table:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e

            # Use scanner with early-stop for limited reads (avoids full table load).
            if limit is not None:
                scanner = dt.to_pyarrow_dataset().scanner(columns=columns)
                return scanner.head(limit)

            return dt.to_pyarrow_table(columns=columns)

        self._logger.debug(
            "Reading Delta table",
            path=str(resolved_path),
            columns=columns,
            limit=limit,
        )

        return await loop.run_in_executor(None, _read)

    async def get_schema(self, table_path: str) -> pa.Schema:
        """Get the schema of a Delta Lake table.

        Args:
            table_path: Path to the Delta table.

        Returns:
            PyArrow Schema describing the table structure.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _get_schema() -> pa.Schema:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e
            return dt.schema().to_arrow()

        return await loop.run_in_executor(None, _get_schema)

    async def get_row_count(self, table_path: str) -> int:
        """Get the number of rows in a Delta Lake table.

        Uses Delta Lake metadata for efficiency when available.

        Args:
            table_path: Path to the Delta table.

        Returns:
            Total number of rows in the table.

        Raises:
            FileNotFoundError: If table does not exist.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _count_rows() -> int:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e

            native_count = getattr(dt, "count", None)
            if callable(native_count):
                try:
                    return int(native_count())
                except (KeyboardInterrupt, SystemExit):
                    raise
                except BaseException:
                    pass  # Why: delta-rs may panic on empty tables; fall through

            # Fallback: re-create DeltaTable (prior call may poison internal lock)
            # and count rows via PyArrow (reads footer metadata, not full data).
            dt_fresh = DeltaTable(str(resolved_path))
            return int(dt_fresh.to_pyarrow_table(columns=[]).num_rows)

        return await loop.run_in_executor(None, _count_rows)

    async def table_exists(self, table_path: str) -> bool:
        """Check if a Delta Lake table exists at the given path.

        Args:
            table_path: Path to check for Delta table.

        Returns:
            True if a valid Delta table exists, False otherwise.
        """
        resolved_path = self._resolve_path(table_path)
        loop = asyncio.get_running_loop()

        def _check_exists() -> bool:
            delta_log = resolved_path / "_delta_log"
            if not delta_log.exists():
                return False
            # Verify it's a valid Delta table
            try:
                DeltaTable(str(resolved_path))
                return True
            except DeltaTableNotFoundError:
                return False

        return await loop.run_in_executor(None, _check_exists)

    async def aclose(self) -> None:
        """Gracefully close the reader (no-op, no persistent resources)."""
