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
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pv

from bioetl.domain.serialization import serialize_to_json

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _is_complex_type(field_type: pa.DataType) -> bool:
    """Check if a PyArrow type is complex (list or struct).

    Returns:
        True if the type is a list, large list, or struct, False otherwise.
    """
    return bool(
        pa.types.is_list(field_type)
        or pa.types.is_large_list(field_type)
        or pa.types.is_struct(field_type)
    )


def _serialize_column_to_json(col: pa.ChunkedArray) -> pa.Array:
    """Serialize a column of complex values to JSON strings.

    Returns:
        PyArrow string array with each value serialized as a JSON string.
    """
    vals = [
        serialize_to_json(val) if (val := v.as_py()) is not None else None for v in col
    ]
    return pa.array(vals, type=pa.string())


def _atomic_csv_write(
    data: pa.Table,
    target_path: Path,
    write_options: pv.WriteOptions,
    logger: LoggerPort,
) -> None:
    """Write CSV atomically to avoid file lock issues on Windows."""
    import time

    target_dir = target_path.parent
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".csv.tmp",
        prefix=target_path.stem + "_",
        dir=target_dir,
    )
    temp_path = Path(temp_path_str)
    try:
        os.close(fd)
        pv.write_csv(data, temp_path, write_options=write_options)
        try:
            temp_path.replace(target_path)
        except PermissionError:
            timestamp = int(time.time())
            backup_path = target_path.with_suffix(f".{timestamp}.csv")
            temp_path.replace(backup_path)
            logger.warning(
                "Target CSV locked, wrote to backup", backup_path=str(backup_path)
            )
            return
    except (OSError, pa.ArrowException, ValueError, TypeError, RuntimeError):
        if temp_path.exists():
            temp_path.unlink()
        raise


def _append_to_csv(
    data: pa.Table,
    csv_path: Path,
    delimiter: str,
    logger: LoggerPort,
) -> None:
    """Append records to an existing CSV without reading it.

    Cost is O(batch_size), not O(total_records).
    """
    import time

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".csv.tmp",
        prefix=csv_path.stem + "_append_",
        dir=csv_path.parent,
    )
    temp_path = Path(temp_path_str)
    try:
        os.close(fd)
        write_options = pv.WriteOptions(include_header=False, delimiter=delimiter)
        pv.write_csv(data, temp_path, write_options=write_options)
        try:
            with open(csv_path, "ab") as target, open(temp_path, "rb") as source:
                target.write(source.read())
        except PermissionError:
            timestamp = int(time.time())
            backup_path = csv_path.with_suffix(f".{timestamp}.csv")
            logger.warning(
                "Target CSV locked during append, wrote batch to backup",
                backup_path=str(backup_path),
            )
            temp_path.replace(backup_path)
            return
    except (OSError, pa.ArrowException, ValueError, TypeError, RuntimeError):
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        if temp_path.exists():
            temp_path.unlink()


def _flatten_table_for_csv(table: pa.Table) -> pa.Table:
    """Convert complex types (list, struct) to JSON strings for CSV export.

    Returns:
        New PyArrow table with complex columns replaced by JSON string columns.
    """
    new_columns = []
    for i, field in enumerate(table.schema):
        col = table.column(i)
        if _is_complex_type(field.type):
            new_columns.append(_serialize_column_to_json(col))
        else:
            new_columns.append(col)

    new_schema = pa.schema(
        [
            pa.field(
                f.name,
                pa.string() if _is_complex_type(f.type) else f.type,
                f.nullable,
            )
            for f in table.schema
        ]
    )
    return pa.Table.from_arrays(new_columns, schema=new_schema)


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
        """Sort table by specified columns for deterministic output.

        Args:
            table: PyArrow table to sort
            sort_columns: Column names to sort by

        Returns:
            Sorted table, or original if columns don't exist

        """
        if not sort_columns:
            return table

        # Filter to columns that exist in schema
        existing_cols = [c for c in sort_columns if c in table.schema.names]
        if not existing_cols:
            return table

        direction = "ascending" if self.sort_ascending else "descending"
        sort_keys = [(col, direction) for col in existing_cols]
        return table.sort_by(sort_keys)

    def _deduplicate(self, table: pa.Table, primary_keys: list[str]) -> pa.Table:
        """Deduplicate table based on primary keys.

        Uses pandas for deduplication as PyArrow lacks direct support.
        Keeps the last occurrence of duplicates.

        Args:
            table: PyArrow table to deduplicate
            primary_keys: List of columns to use as unique key

        Returns:
            Deduplicated PyArrow table
        """
        if not primary_keys:
            return table

        # Verify all primary keys exist in table
        missing_keys = [key for key in primary_keys if key not in table.column_names]
        if missing_keys:
            self._logger.warning(
                "Cannot deduplicate CSV: missing primary keys",
                missing_keys=missing_keys,
            )
            return table

        try:
            # Convert to pandas for deduplication
            df = table.to_pandas()
            original_count = len(df)
            df = df.drop_duplicates(subset=primary_keys, keep="last")
            dedup_count = len(df)

            if dedup_count < original_count:
                self._logger.debug(
                    "Deduplicated CSV data",
                    removed_rows=original_count - dedup_count,
                )

            # Convert back to PyArrow table
            # Use original schema to preserve types
            return pa.Table.from_pandas(df, schema=table.schema)
        except ImportError:
            self._logger.warning("Pandas not available for CSV deduplication")
            return table
        except (
            pa.ArrowException,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RuntimeError,
        ) as e:
            self._logger.warning("CSV deduplication failed", error=str(e))
            return table

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
        csv_full_path = self.base_path / f"{table_name}.csv"
        csv_full_path.parent.mkdir(parents=True, exist_ok=True)
        csv_data = self._flatten_for_csv(data)
        loop = asyncio.get_running_loop()

        # Fast path: true file-append (no read, no sort, no dedup).
        if append and csv_full_path.exists():
            await loop.run_in_executor(
                None,
                lambda: self._append_to_csv(csv_data, csv_full_path),
            )
            return csv_full_path

        # First write or overwrite: sort in executor to avoid blocking event loop.
        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            csv_data = await loop.run_in_executor(
                None,
                lambda: self._sort_table(csv_data, sort_columns),
            )
        write_options = self._build_write_options()
        await loop.run_in_executor(
            None,
            lambda: self._atomic_csv_write(csv_data, csv_full_path, write_options),
        )
        return csv_full_path

    async def finalize_csv(
        self,
        table_name: str,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path | None:
        """Post-run one-shot: read CSV, deduplicate, sort, rewrite.

        Should be called once after all batches complete.  All heavy work
        runs in ``run_in_executor`` to avoid blocking the event loop.

        Args:
            table_name: Logical table name (maps to ``{table_name}.csv``).
            sort_by: Optional column names to sort by; falls back to
                ``self.sort_by`` when *None*.
            primary_keys: Optional column names for deduplication.

        Returns:
            Path to the finalized CSV, or *None* if the file does not exist.
        """
        csv_full_path = self.base_path / f"{table_name}.csv"
        if not csv_full_path.exists():
            return None

        loop = asyncio.get_running_loop()
        parse_options = pv.ParseOptions(delimiter=self.delimiter)

        table: pa.Table = await loop.run_in_executor(
            None,
            lambda: pv.read_csv(csv_full_path, parse_options=parse_options),
        )

        if primary_keys:
            table = await loop.run_in_executor(
                None,
                lambda: self._deduplicate(table, primary_keys),
            )

        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            table = await loop.run_in_executor(
                None,
                lambda: self._sort_table(table, sort_columns),
            )

        write_options = self._build_write_options()
        await loop.run_in_executor(
            None,
            lambda: self._atomic_csv_write(table, csv_full_path, write_options),
        )

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

    def _build_write_options(self) -> pv.WriteOptions:
        """Build CSV writer options from exporter configuration.

        Returns:
            WriteOptions instance configured with the exporter's delimiter and header settings.
        """
        return pv.WriteOptions(
            include_header=self.header,
            delimiter=self.delimiter,
        )
