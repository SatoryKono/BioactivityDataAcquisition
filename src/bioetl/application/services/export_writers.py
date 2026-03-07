"""Writer helpers for export service formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pyarrow as pa


def _write_delimited_file(
    table: pa.Table, output_path: Path, delimiter: str = ","
) -> Path:
    """Write Arrow table to delimited file (CSV or TSV)."""
    import pyarrow.csv as pv

    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    write_options = pv.WriteOptions(delimiter=delimiter)
    pv.write_csv(flattened, output_path, write_options=write_options)
    return output_path


def _write_xlsx_file(table: pa.Table, output_path: Path) -> Path:
    """Write Arrow table to XLSX file."""
    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    df = flattened.to_pandas()

    try:
        df.to_excel(output_path, index=False, engine="openpyxl")
    except ImportError as e:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from e

    return output_path


__all__ = ["_write_delimited_file", "_write_xlsx_file"]
