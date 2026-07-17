"""File writer adapter for export service formats."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import ExportFileFingerprint, ExportWriterPort
from bioetl.infrastructure.storage.atomic import atomic_write_text

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
        output_dir: str,
    ) -> str:
        """Write one exported table and return the created file path."""
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)
        safe_name = f"{layer}_{table_name.replace('.', '_')}"
        if fmt == "csv":
            return str(_write_delimited_file(table, output_dir_obj / f"{safe_name}.csv", ","))
        if fmt == "tsv":
            return str(_write_delimited_file(table, output_dir_obj / f"{safe_name}.tsv", "\t"))
        if fmt == "xlsx":
            return str(_write_xlsx_file(table, output_dir_obj / f"{safe_name}.xlsx"))
        raise ValueError(f"Unsupported format: {fmt}")

    def write_manifest(
        self,
        *,
        manifest_name: str,
        payload: dict[str, object],
        output_dir: str,
    ) -> str:
        """Write one deterministic JSON export manifest and return its path."""
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)
        output_path = output_dir_obj / f"{manifest_name}.json"
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        atomic_write_text(output_path, content)
        return str(output_path)

    def fingerprint_file(self, *, path: str) -> ExportFileFingerprint:
        """Return sha256 and byte size for one exported file."""
        path_obj = Path(path)
        digest = hashlib.sha256()
        size_bytes = 0
        with path_obj.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                size_bytes += len(chunk)
                digest.update(chunk)
        return ExportFileFingerprint(
            path=path,
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
        )


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
