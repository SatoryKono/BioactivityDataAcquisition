"""Pure helpers for DebugExportAdapter persistence and workbook ops."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bioetl.infrastructure.storage.atomic import atomic_write_text

if TYPE_CHECKING:
    from bioetl.domain.types import DebugExportPack

__all__ = [
    "acquire_worksheet",
    "chunk_table_rows",
    "collect_headers",
    "compute_pack_hash",
    "fingerprint_artifact",
    "normalize_csv_value",
    "resolve_debug_export_root",
    "sheet_name_for_chunk",
    "write_debug_csv",
    "write_debug_schema",
    "write_debug_xlsx",
    "write_sheet_rows",
]


def resolve_debug_export_root(pack: DebugExportPack) -> Path:
    configured = Path(pack.output_root)
    if not configured.is_absolute():
        configured = Path.cwd() / configured
    return configured / pack.workflow_id / pack.pipeline_id / pack.run_id


def collect_headers(rows: tuple[dict[str, object], ...]) -> list[str]:
    headers: list[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return headers


def normalize_csv_value(value: object | None) -> object:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_debug_csv(
    output_path: Path,
    rows: tuple[dict[str, object], ...],
    *,
    include_bom: bool,
) -> None:
    headers = collect_headers(rows)
    encoding = "utf-8-sig" if include_bom else "utf-8"
    with output_path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=headers,
            extrasaction="ignore",
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {header: normalize_csv_value(row.get(header)) for header in headers}
            )


def write_debug_schema(
    output_path: Path,
    rows: tuple[dict[str, object], ...],
) -> None:
    headers = collect_headers(rows)
    types = {
        header: sorted(
            {
                type(row.get(header)).__name__
                for row in rows
                if row.get(header) is not None
            }
        )
        for header in headers
    }
    atomic_write_text(
        output_path,
        json.dumps(
            {"columns": [{"name": h, "types": types[h]} for h in headers]},
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def chunk_table_rows(
    rows: tuple[dict[str, object], ...],
    *,
    max_rows_per_sheet: int,
) -> list[tuple[dict[str, object], ...]]:
    chunk_size = max(1, min(max_rows_per_sheet - 1, 1_000_000))
    chunks = [rows[i : i + chunk_size] for i in range(0, len(rows), chunk_size)]
    return chunks or [()]


def sheet_name_for_chunk(table_name: str, chunk_index: int, chunk_count: int) -> str:
    if chunk_count == 1:
        return table_name[:31]
    return f"{table_name}_{chunk_index:04d}"[:31]


def write_sheet_rows(
    worksheet: object,
    *,
    headers: list[str],
    chunk: tuple[dict[str, object], ...],
) -> None:
    # openpyxl Worksheet is duck-typed; keep port surface free of openpyxl types.
    sheet = cast(Any, worksheet)  # Any: openpyxl Worksheet duck-type
    sheet.freeze_panes = "A2"
    sheet.append(headers)
    for row in chunk:
        sheet.append([normalize_csv_value(row.get(header)) for header in headers])
    sheet.auto_filter.ref = sheet.dimensions


def acquire_worksheet(
    workbook: object,
    *,
    sheet_name: str,
    first_sheet: bool,
) -> tuple[object, bool]:
    book = cast(Any, workbook)  # Any: openpyxl Workbook duck-type
    if first_sheet:
        worksheet = book.active
        if worksheet is None:
            raise RuntimeError("new workbook must contain an active worksheet")
        worksheet.title = sheet_name
        return worksheet, False
    return book.create_sheet(title=sheet_name), first_sheet


def write_debug_xlsx(
    output_path: Path,
    tables: dict[str, tuple[dict[str, object], ...]],
    *,
    max_rows_per_sheet: int,
) -> None:
    from openpyxl import Workbook  # pyright: ignore[reportMissingModuleSource]

    workbook = Workbook()
    workbook.properties.created = None
    workbook.properties.modified = None
    first_sheet = True
    for table_name, rows in tables.items():
        headers = collect_headers(rows)
        chunks = chunk_table_rows(rows, max_rows_per_sheet=max_rows_per_sheet)
        for chunk_index, chunk in enumerate(chunks, start=1):
            sheet_name = sheet_name_for_chunk(table_name, chunk_index, len(chunks))
            worksheet, first_sheet = acquire_worksheet(
                workbook, sheet_name=sheet_name, first_sheet=first_sheet
            )
            write_sheet_rows(worksheet, headers=headers, chunk=chunk)
    workbook.save(output_path)


def fingerprint_artifact(
    path: Path,
    *,
    include_content_hash: bool = True,
    root_path: Path | None = None,
) -> dict[str, object]:
    payload = path.read_bytes()
    relative_path = (
        str(path.relative_to(root_path)) if root_path is not None else str(path)
    )
    result: dict[str, object] = {
        "path": relative_path,
        "size_bytes": len(payload),
    }
    if include_content_hash:
        result["sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def compute_pack_hash(artifacts: list[dict[str, object]]) -> str:
    payload = json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()
