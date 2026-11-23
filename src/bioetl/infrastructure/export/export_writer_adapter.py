"""File writer adapter for export service formats."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from openpyxl.cell.cell import Cell, MergedCell
    from openpyxl.workbook.workbook import Workbook
    from pandas import DataFrame

import pyarrow as pa

from bioetl.domain.ports import ExportFileFingerprint, ExportWriterPort
from bioetl.infrastructure.export.csv_exporter_table_ops import spreadsheet_safe_table
from bioetl.infrastructure.export.xlsx_text_parts import write_arrow_xlsx
from bioetl.infrastructure.export.xlsx_workbook import (
    XLSX_EXPORT_MANIFEST_SHEET,
    XLSX_TEXT_PARTS_VERSION,
    read_xlsx_export_manifest,
    restore_xlsx_table,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = [
    "XLSX_EXPORT_MANIFEST_SHEET",
    "XLSX_TEXT_PARTS_VERSION",
    "ExportWriterAdapter",
    "read_xlsx_export_manifest",
    "restore_xlsx_table",
]

_OPENPYXL_REQUIRED = (
    "openpyxl is required for XLSX export. Install with: pip install openpyxl"
)


class ExportWriterAdapter(ExportWriterPort):
    """Write exported tables to CSV, TSV, or XLSX files."""

    def write_export(
        self,
        *,
        table: object,
        table_name: str,
        layer: str,
        fmt: str,
        output_dir: str,
    ) -> str:
        """Write one exported table and return the created file path."""
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)
        safe_name = f"{layer}_{table_name.replace('.', '_')}"
        arrow_table = cast(
            Any, table
        )  # Any: export writer accepts Arrow table duck-type
        if fmt == "csv":
            return str(
                _write_delimited_file(
                    arrow_table, output_dir_obj / f"{safe_name}.csv", ","
                )
            )
        if fmt == "tsv":
            return str(
                _write_delimited_file(
                    arrow_table, output_dir_obj / f"{safe_name}.tsv", "\t"
                )
            )
        if fmt == "xlsx":
            return str(
                _write_xlsx_file(
                    arrow_table,
                    output_dir_obj / f"{safe_name}.xlsx",
                    table_name=table_name,
                    layer=layer,
                )
            )
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
        if manifest_name.endswith(".provenance-manifest"):
            payload = {
                **payload,
                "spreadsheet_text_policy": "csv-tsv-apostrophe-prefix;xlsx-explicit-text;v1",
            }
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
    table: Any,  # Any: Arrow table duck-type for pyarrow.csv
    output_path: Path,
    delimiter: str = ",",
) -> Path:
    """Write Arrow table to delimited text."""
    import pyarrow.csv as pyarrow_csv

    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    write_options = pyarrow_csv.WriteOptions(delimiter=delimiter)
    pyarrow_csv.write_csv(
        spreadsheet_safe_table(flattened), output_path, write_options=write_options
    )
    return output_path


_XLSX_CELL_LIMIT = 32767
_XLSX_PART_SIZE = 32000
_XLSX_PARTS_SHEET = "bioetl_xlsx_parts"
_XLSX_PART_MARKER = "bioetl-xlsx-part:{digest}:{part_count}"


def split_xlsx_text(value: str) -> tuple[str, tuple[str, ...]] | None:
    """Split one over-long cell. Shorter values stay untouched."""
    if len(value) <= _XLSX_CELL_LIMIT:
        return None
    import hashlib

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    parts = tuple(
        value[index : index + _XLSX_PART_SIZE]
        for index in range(0, len(value), _XLSX_PART_SIZE)
    )
    return _XLSX_PART_MARKER.format(digest=digest, part_count=len(parts)), parts


def restore_xlsx_text(token: object, parts: tuple[str, ...]) -> str | None:
    """Restore a split cell only when the part digest matches the token."""
    import hashlib
    import re

    if not isinstance(token, str):
        return None
    matched = re.fullmatch(r"bioetl-xlsx-part:([0-9a-f]{64}):(\d+)", token)
    if matched is None or int(matched.group(2)) != len(parts) or not parts:
        return None
    restored = "".join(parts)
    digest = hashlib.sha256(restored.encode("utf-8")).hexdigest()
    if digest != matched.group(1):
        return None
    return restored


def _xlsx_int(value: object) -> int | None:
    if type(value) is int:
        return value
    return None


def _xlsx_part_groups(
    book: Workbook,
) -> dict[tuple[str, int, int], list[tuple[int, str]]]:
    grouped: dict[tuple[str, int, int], list[tuple[int, str]]] = {}
    if _XLSX_PARTS_SHEET not in book.sheetnames:
        return grouped
    for row in book[_XLSX_PARTS_SHEET].iter_rows(min_row=2, values_only=True):
        sheet, row_number, column, part_index, _digest, _count, value = row
        row_index = _xlsx_int(row_number)
        column_index = _xlsx_int(column)
        part = _xlsx_int(part_index)
        if row_index is None or column_index is None or part is None:
            continue
        grouped.setdefault((str(sheet), row_index, column_index), []).append(
            (part, str(value))
        )
    return grouped


def _restored_cell_value(
    cell: Cell | MergedCell,
    sheet_title: str,
    grouped: dict[tuple[str, int, int], list[tuple[int, str]]],
) -> object:
    row_index = cell.row
    column_index = cell.column
    if row_index is None or column_index is None:
        return cell.value
    ordered = tuple(
        value
        for _index, value in sorted(
            grouped.get((sheet_title, row_index, column_index), [])
        )
    )
    replacement = restore_xlsx_text(cell.value, ordered)
    if replacement is None:
        return cell.value
    return replacement


def restore_xlsx_long_text(path: Path) -> dict[str, list[list[object]]]:
    """Read a workbook and concatenate verified long-text parts."""
    import openpyxl

    book = openpyxl.load_workbook(path)
    grouped = _xlsx_part_groups(book)
    restored: dict[str, list[list[object]]] = {}
    for sheet in book.worksheets:
        if sheet.title == _XLSX_PARTS_SHEET:
            continue
        rows: list[list[object]] = []
        for cells in sheet.iter_rows():
            rows.append(
                [_restored_cell_value(cell, sheet.title, grouped) for cell in cells]
            )
        restored[sheet.title] = rows
    return restored


def _write_xlsx_parts(book: Workbook, parts: list[tuple[object, ...]]) -> None:
    sheet = book.create_sheet(_XLSX_PARTS_SHEET)
    header = (
        "sheet",
        "row",
        "column",
        "part_index",
        "sha256",
        "part_count",
        "value",
    )
    for column, name in enumerate(header, start=1):
        cell = sheet.cell(1, column, name)
        cell.data_type = "s"
    for row_number, record in enumerate(parts, start=2):
        for column, value in enumerate(record, start=1):
            cell = sheet.cell(row_number, column, value)
            if isinstance(value, str):
                cell.data_type = "s"


def _split_xlsx_cells(dataframe: DataFrame) -> list[tuple[object, ...]]:
    """Replace overlong cells before pandas truncates them."""
    parts: list[tuple[object, ...]] = []
    for row_offset, row in enumerate(dataframe.itertuples(index=False)):
        for column_offset, value in enumerate(row):
            if not isinstance(value, str):
                continue
            split = split_xlsx_text(value)
            if split is None:
                continue
            token, chunks = split
            dataframe.iat[row_offset, column_offset] = token
            digest = token.split(":")[1]
            for index, chunk in enumerate(chunks):
                parts.append(
                    (
                        "Sheet1",
                        row_offset + 2,
                        column_offset + 1,
                        index,
                        digest,
                        len(chunks),
                        chunk,
                    )
                )
    return parts


def _write_xlsx_file(
    table: Any,  # Any: Arrow table duck-type for pandas/xlsx export
    output_path: Path,
    *,
    table_name: str = "",
    layer: str = "",
) -> Path:
    """Write one table to XLSX without dropping columns or long text."""
    if isinstance(table, pa.Table):
        return write_arrow_xlsx(
            table,
            output_path,
            table_name=table_name,
            layer=layer,
        )
    return _write_duck_xlsx(table, output_path)


def _write_duck_xlsx(
    table: Any,  # Any: non-Arrow export double with to_pandas
    output_path: Path,
) -> Path:
    """Preserve the pandas path used by non-Arrow export doubles."""
    from bioetl.domain.serialization import flatten_arrow_table_for_export

    flattened = flatten_arrow_table_for_export(table)
    dataframe = flattened.to_pandas()
    try:
        import pandas as pd

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if not writer.book.worksheets:
                writer.book.create_sheet("Sheet1")
            try:
                parts = _split_xlsx_cells(dataframe)
                dataframe.to_excel(writer, index=False, sheet_name="Sheet1")
                if parts:
                    _write_xlsx_parts(writer.book, parts)
            finally:
                # ExcelWriter saves on exceptional exit too: sanitize partial output.
                for sheet in writer.book.worksheets:
                    _force_explicit_text(sheet)
    except ImportError as exc:
        raise ImportError(_OPENPYXL_REQUIRED) from exc
    return output_path


def _force_explicit_text(
    sheet: Any,  # Any: openpyxl worksheet duck type
) -> None:
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"
