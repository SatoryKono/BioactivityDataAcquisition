"""CSV exporter for data layers.

Provides atomic CSV export functionality with support for complex types
(lists, structs) serialization to JSON strings.

Architecture:
- Uses composition pattern - injected into storage writers
- Supports configurable delimiters, headers, encoding
- Implements atomic write for Windows compatibility
- Deterministic output: sorted by specified columns
"""

from __future__ import annotations

__all__ = ["CsvExporter"]

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pv

from bioetl.infrastructure.export.csv_exporter_io_ops import (
    append_to_csv as _append_to_csv,
)
from bioetl.infrastructure.export.csv_exporter_io_ops import (
    atomic_csv_write as _atomic_csv_write,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    deduplicate_table as _deduplicate_table,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    flatten_table_for_csv as _flatten_table_for_csv,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    is_complex_type as _is_complex_type,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    serialize_column_to_json as _serialize_column_to_json,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    sort_table as _sort_table,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class CsvExporter:
    """Exporter for CSV format with atomic writes.

    Handles conversion of complex PyArrow types to CSV-compatible format
    and provides atomic file writes to avoid locking issues.
    """

    # Backward-compatible static aliases used in tests and legacy callers.
    _is_complex_type = staticmethod(_is_complex_type)
    _serialize_column_to_json = staticmethod(_serialize_column_to_json)
    _flatten_for_csv = staticmethod(_flatten_table_for_csv)

    def __init__(
        self,
        base_path: str,
        logger: LoggerPort,
        delimiter: str = ",",
        header: bool = True,
        encoding: str = "utf-8",
        sort_by: list[str] | None = None,
        sort_ascending: bool = True,
    ) -> None:
        """Initialize CSV exporter.

        Args:
            base_path: Base directory for CSV files
            logger: Structured logger for observability (MUST be injected)
            delimiter: Field delimiter (default: ",")
            header: Include header row (default: True)
            encoding: File encoding (default: "utf-8")
            sort_by: Columns to sort by for deterministic output
            sort_ascending: Sort direction (default: ascending)

        """
        self.base_path = Path(base_path)
        self._logger = logger
        self.delimiter = delimiter
        self.header = header
        self.encoding = encoding
        self.sort_by = sort_by or []
        self.sort_ascending = sort_ascending

    def export_table(self, table: pa.Table, output_path: str) -> Path:
        """Synchronously export one table to an explicit CSV path.

        This compatibility surface is retained for integration tests and
        legacy callers that predate the async table-name based exporter API.
        It performs the same CSV shaping steps as the async exporter:
        complex-type flattening, full-row deduplication, optional sorting,
        and atomic write.
        """
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        csv_data = self._flatten_for_csv(table)
        csv_data = self._deduplicate_full_rows(csv_data)
        if self.sort_by:
            csv_data = self._sort_table(csv_data, self.sort_by)

        self._atomic_csv_write(
            csv_data,
            target_path,
            self._build_write_options(),
        )
        return target_path

    def clear(self, table_name: str | None = None) -> list[Path]:
        """Clear CSV files from the export directory.

        Handles PermissionError gracefully on Windows when files are locked.

        Args:
            table_name: Database table name.

        Returns:
            Result list.
        """
        deleted: list[Path] = []
        if not self.base_path.exists():
            return deleted

        files_to_delete = []
        if table_name:
            csv_path = self.base_path / f"{table_name}.csv"
            if csv_path.exists():
                files_to_delete.append(csv_path)
        else:
            files_to_delete = list(self.base_path.glob("*.csv"))

        for csv_file in files_to_delete:
            try:
                csv_file.unlink()
                deleted.append(csv_file)
            except PermissionError:
                self._logger.warning(
                    "Cannot delete locked CSV file",
                    path=str(csv_file),
                    reason="file may be open in another program",
                )

        return deleted

    def _sort_table(self, table: pa.Table, sort_columns: list[str]) -> pa.Table:
        """Sort table by specified columns for deterministic output."""
        return _sort_table(
            table,
            sort_columns,
            sort_ascending=self.sort_ascending,
        )

    def _deduplicate(self, table: pa.Table, primary_keys: list[str]) -> pa.Table:
        """Deduplicate table based on primary keys."""
        return _deduplicate_table(table, primary_keys, logger=self._logger)

    def _atomic_csv_write(
        self,
        data: pa.Table,
        target_path: Path,
        write_options: pv.WriteOptions,
    ) -> None:
        """Write CSV atomically (delegates to module-level function)."""
        _atomic_csv_write(data, target_path, write_options, self._logger)

    async def export(
        self,
        table_name: str,
        data: pa.Table,
        append: bool = True,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path:
        """Export PyArrow table to CSV file.

        When ``append=True`` and the target file exists, new records are
        appended directly without re-reading the existing CSV.  This keeps
        per-batch cost at O(batch_size) instead of O(total_records).
        Call :meth:`finalize_csv` after all batches to deduplicate and sort.

        Returns:
            Path to the written CSV file.
        """
        return await asyncio.to_thread(
            self._export_sync,
            table_name,
            data,
            append,
            sort_by,
            primary_keys,
        )

    def _export_sync(
        self,
        table_name: str,
        data: pa.Table,
        append: bool,
        sort_by: list[str] | None,
        primary_keys: list[str] | None,
    ) -> Path:
        _ = primary_keys
        csv_full_path = self.base_path / f"{table_name}.csv"
        csv_full_path.parent.mkdir(parents=True, exist_ok=True)
        csv_data = self._flatten_for_csv(data)

        # Fast path: true file-append (no read, no sort, no dedup).
        if append and csv_full_path.exists():
            self._append_to_csv(csv_data, csv_full_path)
            return csv_full_path

        # First write or overwrite.
        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            csv_data = self._sort_table(csv_data, sort_columns)
        write_options = self._build_write_options()
        self._atomic_csv_write(csv_data, csv_full_path, write_options)
        return csv_full_path

    async def finalize_csv(
        self,
        table_name: str,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path | None:
        """Post-run one-shot: read CSV, deduplicate, sort, rewrite.

        Should be called once after all batches complete.

        Args:
            table_name: Logical table name (maps to ``{table_name}.csv``).
            sort_by: Optional column names to sort by; falls back to
                ``self.sort_by`` when *None*.
            primary_keys: Optional column names for deduplication.

        Returns:
            Path to the finalized CSV, or *None* if the file does not exist.
        """
        return await asyncio.to_thread(
            self._finalize_csv_sync, table_name, sort_by, primary_keys
        )

    def _finalize_csv_sync(
        self,
        table_name: str,
        sort_by: list[str] | None,
        primary_keys: list[str] | None,
    ) -> Path | None:
        csv_full_path = self.base_path / f"{table_name}.csv"
        if not csv_full_path.exists():
            return None

        parse_options = pv.ParseOptions(delimiter=self.delimiter)

        table = pv.read_csv(csv_full_path, parse_options=parse_options)

        if primary_keys:
            table = self._deduplicate(table, primary_keys)

        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            table = self._sort_table(table, sort_columns)

        write_options = self._build_write_options()
        self._atomic_csv_write(table, csv_full_path, write_options)

        self._logger.info(
            "csv_export_finalized",
            table_name=table_name,
            rows=table.num_rows,
            deduplicated=bool(primary_keys),
            sorted=bool(sort_columns),
        )
        return csv_full_path

    def _append_to_csv(self, data: pa.Table, csv_path: Path) -> None:
        """Append records without reading existing CSV (delegates to module-level)."""
        _append_to_csv(data, csv_path, self.delimiter, self._logger)

    def _deduplicate_full_rows(self, table: pa.Table) -> pa.Table:
        """Drop exact duplicate rows while preserving first-seen order."""
        if table.num_rows < 2:
            return table

        rows = table.to_pylist()
        seen: set[tuple[object, ...]] = set()
        deduplicated_rows: list[dict[str, object]] = []
        column_names = table.column_names

        for row in rows:
            identity = tuple(row.get(column) for column in column_names)
            if identity in seen:
                continue
            seen.add(identity)
            deduplicated_rows.append(row)

        if len(deduplicated_rows) == len(rows):
            return table

        self._logger.debug(
            "csv_export_table_deduplicated",
            removed_rows=len(rows) - len(deduplicated_rows),
        )
        return pa.Table.from_pylist(deduplicated_rows, schema=table.schema)

    def _build_write_options(self) -> pv.WriteOptions:
        """Build CSV writer options from exporter configuration.

        Returns:
            WriteOptions instance configured with the exporter's delimiter and header settings.
        """
        return pv.WriteOptions(
            include_header=self.header,
            delimiter=self.delimiter,
        )
