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

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pv

logger = logging.getLogger(__name__)


class CsvExporter:
    """Exporter for CSV format with atomic writes.

    Handles conversion of complex PyArrow types to CSV-compatible format
    and provides atomic file writes to avoid locking issues.
    """

    def __init__(
        self,
        base_path: str,
        delimiter: str = ",",
        header: bool = True,
        encoding: str = "utf-8",
        sort_by: list[str] | None = None,
        sort_ascending: bool = True,
    ) -> None:
        """Initialize CSV exporter.

        Args:
            base_path: Base directory for CSV files
            delimiter: Field delimiter (default: ",")
            header: Include header row (default: True)
            encoding: File encoding (default: "utf-8")
            sort_by: Columns to sort by for deterministic output
            sort_ascending: Sort direction (default: ascending)

        """
        self.base_path = Path(base_path)
        self.delimiter = delimiter
        self.header = header
        self.encoding = encoding
        self.sort_by = sort_by or []
        self.sort_ascending = sort_ascending

    def clear(self, table_name: str | None = None) -> list[Path]:
        """Clear CSV files from the export directory.

        Handles PermissionError gracefully on Windows when files are locked.
        """
        deleted = []
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
                logger.warning(
                    "Cannot delete locked CSV file: %s (file may be open in another program)",
                    csv_file,
                )

        return deleted

    @staticmethod
    def _is_complex_type(field_type: pa.DataType) -> bool:
        """Check if a PyArrow type is complex (list or struct)."""
        return (
            pa.types.is_list(field_type)
            or pa.types.is_large_list(field_type)
            or pa.types.is_struct(field_type)
        )

    @staticmethod
    def _serialize_column_to_json(col: pa.ChunkedArray) -> pa.Array:
        """Serialize a column of complex values to JSON strings."""
        json_strings = [
            json.dumps(val.as_py(), sort_keys=True) if val.as_py() is not None else None
            for val in col
        ]
        return pa.array(json_strings, type=pa.string())

    @staticmethod
    def _flatten_for_csv(table: pa.Table) -> pa.Table:
        """Convert complex types (list, struct) to JSON strings for CSV export."""
        new_columns = []
        for i, field in enumerate(table.schema):
            col = table.column(i)
            if CsvExporter._is_complex_type(field.type):
                new_columns.append(CsvExporter._serialize_column_to_json(col))
            else:
                new_columns.append(col)

        new_schema = pa.schema(
            [
                pa.field(
                    f.name,
                    pa.string() if CsvExporter._is_complex_type(f.type) else f.type,
                    f.nullable,
                )
                for f in table.schema
            ]
        )
        return pa.Table.from_arrays(new_columns, schema=new_schema)

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

    @staticmethod
    def _atomic_csv_write(
        data: pa.Table,
        target_path: Path,
        write_options: pv.WriteOptions,
    ) -> None:
        """Write CSV atomically to avoid file lock issues on Windows.

        If target file is locked, writes to a timestamped backup file instead.
        """
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

            # Use os.replace for atomic overwrite (works on Windows and Unix)
            try:
                os.replace(temp_path, target_path)
            except PermissionError:
                # File is locked by another process - use backup filename
                timestamp = int(time.time())
                backup_path = target_path.with_suffix(f".{timestamp}.csv")
                os.replace(temp_path, backup_path)
                logger.warning(
                    "Target CSV locked, wrote to backup: %s", backup_path
                )
                return
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def export(
        self,
        table_name: str,
        data: pa.Table,
        append: bool = True,
        sort_by: list[str] | None = None,
    ) -> Path:
        """Export PyArrow table to CSV file.

        Args:
            table_name: Name of the table (used for file naming)
            data: PyArrow table to export
            append: If True, append to existing file; if False, overwrite
            sort_by: Override default sort columns for this export

        Returns:
            Path to the written CSV file

        """
        csv_full_path = self.base_path / f"{table_name}.csv"
        csv_full_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert list/struct columns to JSON strings for CSV compatibility
        csv_data = self._flatten_for_csv(data)

        # If append mode and file exists, read and concatenate
        if append and csv_full_path.exists():
            loop = asyncio.get_running_loop()
            csv_data = await loop.run_in_executor(
                None,
                lambda: self._read_and_concat(csv_full_path, csv_data),
            )

        # Sort for deterministic output
        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            csv_data = self._sort_table(csv_data, sort_columns)

        # Build CSV write options
        write_options = pv.WriteOptions(
            include_header=self.header,
            delimiter=self.delimiter,
        )

        # Atomic write in executor to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._atomic_csv_write(csv_data, csv_full_path, write_options),
        )

        return csv_full_path

    def _read_and_concat(self, existing_path: Path, new_data: pa.Table) -> pa.Table:
        """Read existing CSV and concatenate with new data."""
        parse_options = pv.ParseOptions(delimiter=self.delimiter)

        column_types = {field.name: field.type for field in new_data.schema}
        convert_options = pv.ConvertOptions(column_types=column_types)

        try:
            existing_table = pv.read_csv(
                existing_path,
                parse_options=parse_options,
                convert_options=convert_options,
            )

            return pa.concat_tables([existing_table, new_data])
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            return new_data
