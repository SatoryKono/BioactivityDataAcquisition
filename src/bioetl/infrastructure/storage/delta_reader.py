"""Delta Lake reader for table access and export."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import (
    TableNotFoundError as DeltaTableNotFoundError,
)

from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow
from bioetl.infrastructure.storage.delta_reader_helpers import (
    FULL_READ_HEAD_LIMIT as _FULL_READ_HEAD_LIMIT,
)
from bioetl.infrastructure.storage.delta_reader_helpers import (
    count_delta_rows as _count_delta_rows_impl,
)
from bioetl.infrastructure.storage.delta_reader_helpers import (
    try_native_delta_row_count as _try_native_delta_row_count,
)
from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_read_candidates,
    resolve_versioned_table_name,
)

__all__ = ["DeltaReader"]

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _count_delta_rows(dt: DeltaTable, resolved_path: Path) -> int:
    """Return row count using metadata when available."""
    return _count_delta_rows_impl(
        dt,
        resolved_path,
        delta_table_factory=DeltaTable,
    )


class DeltaReader:
    """Read-only accessor for Delta Lake tables."""

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
        if "/" not in table_path and "\\" not in table_path and "." in table_path:
            provider, remainder = table_path.split(".", 1)
            return self._base_path / provider / remainder
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

        def _read() -> pa.Table:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e

            scanner = dt.to_pyarrow_dataset().scanner(columns=columns)
            if limit is not None:
                return scanner.head(limit)

            row_count = _try_native_delta_row_count(dt)
            return scanner.head(
                row_count if row_count is not None else _FULL_READ_HEAD_LIMIT
            )

        self._logger.debug(
            "Reading Delta table",
            path=str(resolved_path),
            columns=columns,
            limit=limit,
        )

        return _read()

    async def read_versioned_table(
        self,
        logical_table: str,
        contract_version: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read a versioned physical table for one logical contract version."""
        return await self.read_table(
            resolve_versioned_table_name(logical_table, contract_version),
            columns=columns,
            limit=limit,
        )

    async def read_with_fallback(
        self,
        logical_table: str,
        read_order: list[str],
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read the first available versioned table in fallback order."""
        missing_errors: list[FileNotFoundError] = []
        for candidate in resolve_read_candidates(logical_table, read_order):
            try:
                return await self.read_table(candidate, columns=columns, limit=limit)
            except FileNotFoundError as exc:
                missing_errors.append(exc)
        if missing_errors:
            raise missing_errors[0]
        raise FileNotFoundError(f"No read candidates configured for {logical_table}")

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

        def _get_schema() -> pa.Schema:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e
            return delta_schema_to_pyarrow(dt.schema())

        return _get_schema()

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

        def _count_rows() -> int:
            try:
                dt = DeltaTable(str(resolved_path))
            except DeltaTableNotFoundError as e:
                raise FileNotFoundError(
                    f"Delta table not found: {resolved_path}"
                ) from e

            return _count_delta_rows(dt, resolved_path)

        return _count_rows()

    async def table_exists(self, table_path: str) -> bool:
        """Check if a Delta Lake table exists at the given path.

        Args:
            table_path: Path to check for Delta table.

        Returns:
            True if a valid Delta table exists, False otherwise.
        """
        resolved_path = self._resolve_path(table_path)

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

        # Keep filesystem/Delta existence checks off the event loop (ARCH-CR-01 / #6863).
        return await asyncio.to_thread(_check_exists)

    async def aclose(self) -> None:
        """Gracefully close the reader (no-op, no persistent resources)."""
        await asyncio.sleep(0)
