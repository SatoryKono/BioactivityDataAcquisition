"""Openpyxl workbook IO and XLSX value restoration."""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pyarrow as pa

from bioetl.infrastructure.export.xlsx_value_codec import (
    _apply_empty_strings,
    _optional_string_list,
    _require_empty_strings,
    _require_part_map,
    _require_string_list,
    is_structured_type,
    is_text_type,
    table_from_xlsx_rows,
    value_type,
)

__all__ = [
    "XLSX_EXPORT_MANIFEST_SHEET",
    "XLSX_MAX_CELL_CHARS",
    "XLSX_TEXT_PARTS_VERSION",
    "is_structured_type",
    "is_text_type",
    "load_xlsx_workbook",
    "new_xlsx_workbook",
    "read_xlsx_export_manifest",
    "restore_xlsx_table",
    "save_xlsx_workbook",
    "split_xlsx_text",
    "stamp_xlsx_workbook",
    "value_type",
    "write_xlsx_manifest_sheet",
    "write_xlsx_table_sheet",
]

XLSX_TEXT_PARTS_VERSION = "xlsx-text-parts-v1"
XLSX_EXPORT_MANIFEST_SHEET = "_bioetl_export_manifest"
XLSX_MAX_CELL_CHARS = 32767
_OPENPYXL_REQUIRED = (
    "openpyxl is required for XLSX export. Install with: pip install openpyxl"
)


def split_xlsx_text(value: str) -> list[str]:
    """Split one string on the OOXML cell-length limit."""
    if len(value) <= XLSX_MAX_CELL_CHARS:
        return [value]
    return [
        value[index : index + XLSX_MAX_CELL_CHARS]
        for index in range(0, len(value), XLSX_MAX_CELL_CHARS)
    ]


def read_xlsx_export_manifest(path: str) -> dict[str, object]:
    """Return the text-part manifest embedded in one XLSX export."""
    workbook = load_xlsx_workbook(path)
    try:
        return _read_manifest_workbook(workbook)
    finally:
        workbook.close()


def restore_xlsx_table(path: str) -> pa.Table:
    """Rebuild exported columns, including text split across XLSX cells."""
    manifest = read_xlsx_export_manifest(path)
    source_columns = _require_string_list(
        manifest.get("source_columns"), "source_columns"
    )
    part_columns = _require_part_map(manifest.get("part_columns"))
    data_sheet_name = manifest.get("data_sheet")
    if not isinstance(data_sheet_name, str) or not data_sheet_name:
        raise ValueError("xlsx manifest data_sheet is missing")
    workbook = load_xlsx_workbook(path)
    try:
        if data_sheet_name not in workbook.sheetnames:
            raise ValueError("xlsx data sheet is missing")
        records = _sheet_records(workbook[data_sheet_name])
    finally:
        workbook.close()
    _apply_empty_strings(records, _require_empty_strings(manifest.get("empty_strings")))
    rows = _restore_rows(records, source_columns, part_columns)
    expected_rows = manifest.get("row_count")
    if (
        isinstance(expected_rows, int)
        and not isinstance(expected_rows, bool)
        and len(rows) != expected_rows
    ):
        raise ValueError("xlsx row count does not match the export manifest")
    numeric_text_columns = set(
        _optional_string_list(manifest.get("numeric_text_columns")) or ()
    )
    if not numeric_text_columns <= set(source_columns):
        raise ValueError("xlsx numeric text column is missing")
    return table_from_xlsx_rows(
        rows,
        source_columns,
        _optional_string_list(manifest.get("column_types")),
        numeric_text_columns=numeric_text_columns,
    )


def write_xlsx_table_sheet(
    worksheet: Any,  # Any: openpyxl worksheet duck type
    table: pa.Table,
) -> list[str]:
    """Write one Arrow table and return columns needing exact numeric text."""
    headers = list(table.column_names)
    numeric_text_columns: set[str] = set()
    for column_index, header in enumerate(headers, start=1):
        _write_text(worksheet, 1, column_index, header)
    columns = [
        cast(list[object], table.column(index).to_pylist())
        for index in range(table.num_columns)
    ]
    for row_offset, values in enumerate(zip(*columns, strict=True), start=2):
        wrote = False
        for column_index, value in enumerate(values, start=1):
            if value is None:
                continue
            wrote = True
            if _needs_numeric_text(value):
                numeric_text_columns.add(headers[column_index - 1])
                _write_text(worksheet, row_offset, column_index, str(value))
            else:
                _write_value(worksheet, row_offset, column_index, value)
        if not wrote:
            # openpyxl omits a cell whose value is None, so a trailing all-null
            # row disappears on load. An empty string reads back as None.
            _write_text(worksheet, row_offset, 1, "")
    return sorted(numeric_text_columns)


def write_xlsx_manifest_sheet(
    workbook: Any,  # Any: openpyxl workbook duck type
    manifest: dict[str, object],
) -> None:
    """Store the canonical manifest JSON in cell-sized chunks."""
    payload = json.dumps(
        manifest,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    chunks = split_xlsx_text(payload)
    sheet = workbook.create_sheet(XLSX_EXPORT_MANIFEST_SHEET)
    _write_text(sheet, 1, 1, XLSX_TEXT_PARTS_VERSION)
    sheet.cell(2, 1, len(chunks))
    for offset, chunk in enumerate(chunks, start=3):
        _write_text(sheet, offset, 1, chunk)


def stamp_xlsx_workbook(
    workbook: Any,  # Any: openpyxl workbook duck type
) -> None:
    """Stamp a fixed created/modified time for a deterministic package."""
    created = datetime(1980, 1, 1)
    workbook.properties.created = created
    workbook.properties.modified = created


def save_xlsx_workbook(
    workbook: Any,  # Any: openpyxl workbook duck type
    output_path: Path,
) -> None:
    """Atomically replace the XLSX after a successful save."""
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    try:
        workbook.save(temporary)
        temporary.replace(output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
        workbook.close()


def new_xlsx_workbook() -> Any:  # Any: openpyxl workbook duck type
    """Create one workbook or raise a stable import error."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ImportError(_OPENPYXL_REQUIRED) from exc
    return Workbook()


def load_xlsx_workbook(path: str) -> Any:  # Any: openpyxl workbook duck type
    """Load one workbook or raise a stable import error."""
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ImportError(_OPENPYXL_REQUIRED) from exc
    return load_workbook(path, data_only=False)


def _needs_numeric_text(value: object) -> bool:
    """Detect numbers that native Excel cells cannot preserve exactly."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return abs(value) >= 10**15
    if not isinstance(value, float):
        return False
    if value == 0.0:
        return math.copysign(1.0, value) < 0
    magnitude = abs(value)
    return (
        not math.isfinite(value)
        or magnitude < sys.float_info.min
        or magnitude >= 1e308
        or float(format(value, ".15g")) != value
    )


def _write_value(
    worksheet: Any,  # Any: openpyxl worksheet duck type
    row: int,
    column: int,
    value: object,
) -> None:
    if isinstance(value, (bool, int, float)):
        worksheet.cell(row, column, value)
    else:
        _write_text(worksheet, row, column, str(value))


def _write_text(
    worksheet: Any,  # Any: openpyxl worksheet duck type
    row: int,
    column: int,
    value: str,
) -> None:
    if len(value) > XLSX_MAX_CELL_CHARS:
        raise ValueError("XLSX cell exceeds 32767 characters after splitting")
    cell = worksheet.cell(row, column, value)
    # openpyxl would store a leading "=" as a formula. Explicit text keeps the
    # characters and does not add the CSV apostrophe prefix.
    cell.data_type = "s"


def _read_manifest_workbook(
    workbook: Any,  # Any: openpyxl workbook duck type
) -> dict[str, object]:
    if XLSX_EXPORT_MANIFEST_SHEET not in workbook.sheetnames:
        raise ValueError("xlsx export manifest sheet is missing")
    sheet = workbook[XLSX_EXPORT_MANIFEST_SHEET]
    if sheet.cell(1, 1).value != XLSX_TEXT_PARTS_VERSION:
        raise ValueError("unsupported xlsx export manifest")
    count = sheet.cell(2, 1).value
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("xlsx export manifest chunk count is invalid")
    chunks: list[str] = []
    for offset in range(count):
        chunk = sheet.cell(3 + offset, 1).value
        if not isinstance(chunk, str):
            raise ValueError("xlsx export manifest chunk is not text")
        chunks.append(chunk)
    payload = json.loads("".join(chunks))
    if not isinstance(payload, dict):
        raise ValueError("xlsx export manifest must be an object")
    return cast(dict[str, object], payload)


def _sheet_records(
    sheet: Any,  # Any: openpyxl worksheet duck type
) -> list[dict[str, object]]:
    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        raise ValueError("xlsx data sheet has no header")
    headers = ["" if cell is None else str(cell) for cell in header]
    records: list[dict[str, object]] = []
    width = len(headers)
    for row in rows:
        values = list(row[:width])
        if len(values) < width:
            values.extend([None] * (width - len(values)))
        records.append(dict(zip(headers, values, strict=True)))
    return records


def _restore_rows(
    records: list[dict[str, object]],
    source_columns: list[str],
    part_columns: dict[str, list[str]],
) -> list[dict[str, object]]:
    restored: list[dict[str, object]] = []
    for record in records:
        row = {
            name: (
                _join_parts(record, part_columns[name])
                if name in part_columns
                else record.get(name)
            )
            for name in source_columns
        }
        restored.append(row)
    return restored


def _join_parts(record: dict[str, object], parts: list[str]) -> str | None:
    missing = [name for name in parts if name not in record]
    if missing:
        raise ValueError(f"xlsx text parts missing columns: {missing}")
    chunks = [record[name] for name in parts]
    if all(chunk is None for chunk in chunks):
        return None
    text: list[str] = []
    for chunk in chunks:
        if chunk is None:
            continue
        if not isinstance(chunk, str):
            raise ValueError("xlsx text part is not stored as text")
        text.append(chunk)
    return "".join(text)
