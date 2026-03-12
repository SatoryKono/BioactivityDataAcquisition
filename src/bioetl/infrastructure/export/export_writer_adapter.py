"""File writer adapter for export service formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import ExportWriterPort

if TYPE_CHECKING:
    import pyarrow as pa

__all__ = ["ExportWriterAdapter"]


class ExportWriterAdapter(ExportWriterPort):
    """Write exported tables to CSV, TSV, or XLSX files."""

    def write_export(
        self,
        *,
        table: pa.Table,
        table_name: str,
        layer: str,
        fmt: str,
        output_dir: Path,
    ) -> Path:
        """Write one exported table and return the created file path."""
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{layer}_{table_name.replace('.', '_')}"
        if fmt == "csv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.csv", ",")
        if fmt == "tsv":
            return _write_delimited_file(table, output_dir / f"{safe_name}.tsv", "\t")
        if fmt == "xlsx":
            return _write_xlsx_file(table, output_dir / f"{safe_name}.xlsx")
        raise ValueError(f"Unsupported format: {fmt}")


def _write_delimited_file(
    table: pa.Table,
    output_path: Path,
    delimiter: str = ",",
) -> Path:
    """Write Arrow table to delimited text."""
    import pyarrow.csv as pyarrow_csv

    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    write_options = pyarrow_csv.WriteOptions(delimiter=delimiter)
    pyarrow_csv.write_csv(flattened, output_path, write_options=write_options)
    return output_path


def _write_xlsx_file(table: pa.Table, output_path: Path) -> Path:
    """Write Arrow table to XLSX."""
    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    dataframe = flattened.to_pandas()

    try:
        dataframe.to_excel(output_path, index=False, engine="openpyxl")
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from exc

    return output_path
