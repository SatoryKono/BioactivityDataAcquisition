"""CSV exporter for data layers.

Provides atomic CSV export functionality with support for complex types
(lists, structs) serialization to JSON strings.

Architecture:
- Uses composition pattern - injected into storage writers
- Supports configurable delimiters, headers, encoding
- Implements atomic write for Windows compatibility
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pv


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
    ) -> None:
        """Initialize CSV exporter.

        Args:
            base_path: Base directory for CSV files
            delimiter: Field delimiter (default: ",")
            header: Include header row (default: True)
            encoding: File encoding (default: "utf-8")
        """
        self.base_path = Path(base_path)
        self.delimiter = delimiter
        self.header = header
        self.encoding = encoding

    def clear(self, table_name: str | None = None) -> list[Path]:
        """Clear CSV files from the export directory.

        Args:
            table_name: If provided, only clear CSV for this table.
                       If None, clear all CSV files in base_path.

        Returns:
            List of deleted file paths.
        """
        deleted = []
        if not self.base_path.exists():
            return deleted

        if table_name:
            # Clear specific table CSV
            csv_path = self.base_path / f"{table_name}.csv"
            if csv_path.exists():
                csv_path.unlink()
                deleted.append(csv_path)
        else:
            # Clear all CSV files in base_path
            for csv_file in self.base_path.glob("*.csv"):
                csv_file.unlink()
                deleted.append(csv_file)

        return deleted

    @staticmethod
    def _flatten_for_csv(table: pa.Table) -> pa.Table:
        """Convert complex types (list, struct) to JSON strings for CSV export.

        Args:
            table: PyArrow table with potentially complex types

        Returns:
            PyArrow table with complex types serialized to JSON strings
        """
        new_columns = []
        for i, field in enumerate(table.schema):
            col = table.column(i)
            if (
                pa.types.is_list(field.type)
                or pa.types.is_large_list(field.type)
                or pa.types.is_struct(field.type)
            ):
                json_strings = [
                    json.dumps(val.as_py()) if val.as_py() is not None else None
                    for val in col
                ]
                new_columns.append(pa.array(json_strings, type=pa.string()))
            else:
                new_columns.append(col)

        new_schema = pa.schema(
            [
                pa.field(
                    f.name,
                    (
                        pa.string()
                        if pa.types.is_list(f.type)
                        or pa.types.is_large_list(f.type)
                        or pa.types.is_struct(f.type)
                        else f.type
                    ),
                    f.nullable,
                )
                for f in table.schema
            ]
        )
        return pa.Table.from_arrays(new_columns, schema=new_schema)

    @staticmethod
    def _atomic_csv_write(
        data: pa.Table,
        target_path: Path,
        write_options: pv.WriteOptions,
    ) -> None:
        """Write CSV atomically to avoid file lock issues on Windows.

        Writes to a temporary file in the same directory, then renames.
        This avoids WinError 32 when the target file is briefly locked.

        Args:
            data: PyArrow table to write
            target_path: Destination file path
            write_options: PyArrow CSV write options
        """
        target_dir = target_path.parent
        fd, temp_path_str = tempfile.mkstemp(
            suffix=".csv.tmp",
            prefix=target_path.stem + "_",
            dir=target_dir,
        )
        temp_path = Path(temp_path_str)
        try:
            os.close(fd)  # Close fd, PyArrow will open by path
            pv.write_csv(data, temp_path, write_options=write_options)

            # On Windows, need to remove target first if exists
            if os.name == "nt" and target_path.exists():
                target_path.unlink()

            # Atomic rename
            temp_path.rename(target_path)
        except Exception:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def export(
        self,
        table_name: str,
        data: pa.Table,
        append: bool = True,
    ) -> Path:
        """Export PyArrow table to CSV file.

        Args:
            table_name: Name of the table (used for file naming)
            data: PyArrow table to export
            append: If True, append to existing file; if False, overwrite

        Returns:
            Path to the written CSV file
        """
        # Construct target path
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
        """Read existing CSV and concatenate with new data.

        Args:
            existing_path: Path to existing CSV file
            new_data: New data to append

        Returns:
            Concatenated PyArrow table
        """
        read_options = pv.ReadOptions()
        parse_options = pv.ParseOptions(delimiter=self.delimiter)

        existing_table = pv.read_csv(
            existing_path,
            read_options=read_options,
            parse_options=parse_options,
        )

        # Concatenate tables
        return pa.concat_tables([existing_table, new_data])
