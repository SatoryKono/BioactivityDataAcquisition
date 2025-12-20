"""CSV Export Logic.

Separated from DeltaWriter to adhere to Single Responsibility Principle.
Handles flattening of complex types and atomic writing to avoid file locking issues.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pv


class CsvExporter:
    """Handles CSV export functionality."""

    def __init__(
        self,
        base_path: str | None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize CsvExporter.

        Args:
            base_path: Root path for CSV exports (None to disable)
            options: CSV export options (delimiter, header, encoding)
        """
        self.base_path = base_path
        self.options = options or {}

    @staticmethod
    def _flatten_for_csv(table: pa.Table) -> pa.Table:
        """Convert complex types (list, struct) to JSON strings for CSV export."""
        new_columns = []
        for i, field in enumerate(table.schema):
            col = table.column(i)
            if pa.types.is_list(field.type) or pa.types.is_large_list(field.type) or pa.types.is_struct(field.type):
                json_strings = [
                    json.dumps(val.as_py()) if val.as_py() is not None else None
                    for val in col
                ]
                new_columns.append(pa.array(json_strings, type=pa.string()))
            else:
                new_columns.append(col)

        new_schema = pa.schema([
            pa.field(f.name, pa.string() if pa.types.is_list(f.type) or pa.types.is_large_list(f.type) or pa.types.is_struct(f.type) else f.type, f.nullable)
            for f in table.schema
        ])
        return pa.Table.from_arrays(new_columns, schema=new_schema)

    def _atomic_csv_write(
        self,
        data: pa.Table,
        target_path: Path,
        write_options: pv.WriteOptions,
    ) -> None:
        """Write CSV atomically to avoid file lock issues on Windows.

        Writes to a temporary file in the same directory, then renames.
        """
        # Create temp file in same directory for atomic rename
        target_dir = target_path.parent
        fd, temp_path = tempfile.mkstemp(
            suffix=".csv.tmp",
            prefix=target_path.stem + "_",
            dir=target_dir,
        )
        try:
            os.close(fd)  # Close fd, PyArrow will open by path
            pv.write_csv(data, temp_path, write_options=write_options)

            # On Windows, need to remove target first if exists
            if os.name == "nt" and target_path.exists():
                target_path.unlink()

            # Atomic rename
            os.rename(temp_path, target_path)
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    async def export(self, table_name: str, arrow_data: pa.Table) -> None:
        """Export data to CSV if enabled."""
        if not self.base_path:
            return

        csv_full_path = Path(self.base_path) / f"{table_name}.csv"
        csv_full_path.parent.mkdir(parents=True, exist_ok=True)

        # Build CSV write options from config
        delimiter = self.options.get("delimiter", ",")
        include_header = self.options.get("header", True)

        write_options = pv.WriteOptions(
            include_header=include_header,
            delimiter=delimiter,
        )

        # Convert list/struct columns to JSON strings for CSV compatibility
        csv_data = self._flatten_for_csv(arrow_data)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._atomic_csv_write(csv_data, csv_full_path, write_options)
        )
