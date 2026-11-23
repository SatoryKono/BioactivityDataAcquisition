"""File writer adapter for export service formats."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pyarrow as pa

from bioetl.domain.ports import ExportFileFingerprint, ExportWriterPort
from bioetl.domain.serialization import serialize_to_json
from bioetl.infrastructure.export.csv_exporter_table_ops import spreadsheet_safe_table
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = [
    "XLSX_EXPORT_MANIFEST_SHEET",
    "XLSX_TEXT_PARTS_VERSION",
    "ExportWriterAdapter",
    "read_xlsx_export_manifest",
    "restore_xlsx_table",
]

XLSX_TEXT_PARTS_VERSION = "xlsx-text-parts-v1"
XLSX_EXPORT_MANIFEST_SHEET = "_bioetl_export_manifest"
_DATA_SHEET_NAME = "Sheet1"
_PART_SUFFIX = "__bioetl_part_"
_TABLE_VERSION_METADATA_KEY = b"bioetl.table_version"
_XLSX_MAX_CELL_CHARS = 32767
_XLSX_MAX_COLUMNS = 16384
_XLSX_MAX_ROWS = 1048576
_RUN_ID_COLUMNS = ("_run_id", "run_id")
_PROFILE_COLUMN = "target_class_profile_sha256"
_VERSION_COLUMNS = ("table_version", "delta_version")


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


def read_xlsx_export_manifest(path: str) -> dict[str, object]:
    """Return the text-part manifest embedded in one XLSX export."""
    workbook = _load_workbook(path)
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
    workbook = _load_workbook(path)
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
    return _table_from_rows(rows, source_columns)


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


def _write_xlsx_file(
    table: Any,  # Any: Arrow table duck-type for pandas/xlsx export
    output_path: Path,
    *,
    table_name: str = "",
    layer: str = "",
) -> Path:
    """Write one table to XLSX without dropping columns or long text."""
    if isinstance(table, pa.Table):
        return _write_arrow_xlsx(
            table,
            output_path,
            table_name=table_name,
            layer=layer,
        )
    return _write_duck_xlsx(table, output_path)


def _write_arrow_xlsx(
    table: pa.Table,
    output_path: Path,
    *,
    table_name: str,
    layer: str,
) -> Path:
    """Write an Arrow table with canonical structured values and text parts."""
    if table.num_rows > _XLSX_MAX_ROWS - 1:
        raise ValueError("XLSX export exceeds 1048576 rows")
    canonical = _canonicalize_structured_columns(table)
    expanded, part_columns = _expand_long_text(canonical)
    manifest = _export_manifest(
        canonical,
        table_name=table_name,
        layer=layer,
        part_columns=part_columns,
        empty_strings=_empty_string_index(expanded),
    )
    workbook = _new_workbook()
    worksheet = workbook.active
    worksheet.title = _DATA_SHEET_NAME
    _write_table_sheet(worksheet, expanded)
    _write_manifest_sheet(workbook, manifest)
    _stamp_workbook(workbook)
    _save_workbook(workbook, output_path)
    return output_path


def _write_duck_xlsx(table: Any, output_path: Path) -> Path:
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
                dataframe.to_excel(writer, index=False)
            finally:
                for sheet in writer.book.worksheets:
                    _force_explicit_text(sheet)
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from exc
    return output_path


def _canonicalize_structured_columns(table: pa.Table) -> pa.Table:
    """Serialize list, struct, and map columns to canonical JSON strings."""
    arrays: list[pa.Array | pa.ChunkedArray] = []
    fields: list[pa.Field] = []
    changed = False
    for index, field in enumerate(table.schema):
        logical = _value_type(field.type)
        if not _is_structured_type(logical):
            arrays.append(table.column(index))
            fields.append(field)
            continue
        arrays.append(
            _canonical_json_array(
                table.column(index),
                as_map=pa.types.is_map(logical),
            )
        )
        fields.append(pa.field(field.name, pa.large_string(), field.nullable))
        changed = True
    if not changed:
        return table
    return pa.Table.from_arrays(
        arrays,
        schema=pa.schema(fields, metadata=table.schema.metadata),
    )


def _canonical_json_array(column: pa.ChunkedArray, *, as_map: bool) -> pa.Array:
    values: list[str | None] = []
    for value in column.to_pylist():
        if value is None:
            values.append(None)
            continue
        payload = _map_object(value) if as_map else value
        if not isinstance(payload, (dict, list)):
            raise TypeError("structured export value must be an object or array")
        values.append(serialize_to_json(payload))
    return pa.array(values, type=pa.large_string())


def _map_object(value: object) -> dict[str, object]:
    if not isinstance(value, list):
        raise TypeError("map export value must be a list of pairs")
    ready: dict[str, object] = {}
    for item in value:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("map export entry must be a pair")
        key, nested = item
        ready[key if isinstance(key, str) else str(key)] = nested
    return ready


def _expand_long_text(table: pa.Table) -> tuple[pa.Table, dict[str, list[str]]]:
    """Split strings that openpyxl would otherwise truncate at 32767 chars."""
    source_names = list(table.column_names)
    occupied = set(source_names)
    part_columns: dict[str, list[str]] = {}
    arrays: list[pa.Array | pa.ChunkedArray] = []
    fields: list[pa.Field] = []
    for index, name in enumerate(source_names):
        field = table.schema.field(index)
        logical = _value_type(field.type)
        column = table.column(index)
        if not _is_text_type(logical):
            arrays.append(column)
            fields.append(field)
            continue
        pieces = _split_column(column)
        names = _part_names(name, _part_width(pieces))
        _reject_part_collisions(name, names, occupied)
        if len(names) > 1:
            part_columns[name] = names
        for extra in names[1:]:
            occupied.add(extra)
        _append_text_parts(arrays, fields, field, column, pieces, names)
    expanded = pa.Table.from_arrays(
        arrays,
        schema=pa.schema(fields, metadata=table.schema.metadata),
    )
    if expanded.num_columns > _XLSX_MAX_COLUMNS:
        raise ValueError("XLSX export exceeds 16384 columns after text splitting")
    return expanded, part_columns


def _split_column(column: pa.ChunkedArray) -> list[list[str] | None]:
    return [
        None if value is None else _split_text(value) for value in column.to_pylist()
    ]


def _split_text(value: str) -> list[str]:
    if len(value) <= _XLSX_MAX_CELL_CHARS:
        return [value]
    return [
        value[index : index + _XLSX_MAX_CELL_CHARS]
        for index in range(0, len(value), _XLSX_MAX_CELL_CHARS)
    ]


def _part_width(pieces: list[list[str] | None]) -> int:
    return max((len(item) for item in pieces if item is not None), default=1)


def _part_names(column: str, width: int) -> list[str]:
    return [_part_name(column, part_number) for part_number in range(1, width + 1)]


def _part_name(column: str, part_number: int) -> str:
    if part_number == 1:
        return column
    return f"{column}{_PART_SUFFIX}{part_number:04d}"


def _reject_part_collisions(column: str, names: list[str], occupied: set[str]) -> None:
    extras = names[1:]
    if len(extras) != len(set(extras)) or any(part in occupied for part in extras):
        raise ValueError(f"XLSX text-part column name collides for {column!r}")


def _append_text_parts(
    arrays: list[pa.Array | pa.ChunkedArray],
    fields: list[pa.Field],
    field: pa.Field,
    column: pa.ChunkedArray,
    pieces: list[list[str] | None],
    names: list[str],
) -> None:
    if len(names) == 1:
        arrays.append(column)
        fields.append(field)
        return
    for part_index, name in enumerate(names):
        part_values = [
            None if item is None or part_index >= len(item) else item[part_index]
            for item in pieces
        ]
        arrays.append(pa.array(part_values, type=pa.large_string()))
        fields.append(pa.field(name, pa.large_string(), nullable=True))


def _export_manifest(
    table: pa.Table,
    *,
    table_name: str,
    layer: str,
    part_columns: dict[str, list[str]],
    empty_strings: dict[str, list[int]],
) -> dict[str, object]:
    return {
        "data_sheet": _DATA_SHEET_NAME,
        "empty_strings": empty_strings,
        "identity": _export_identity(table),
        "layer": layer,
        "max_cell_chars": _XLSX_MAX_CELL_CHARS,
        "part_columns": part_columns,
        "row_count": table.num_rows,
        "schema_version": XLSX_TEXT_PARTS_VERSION,
        "source_columns": list(table.column_names),
        "table_name": table_name,
    }


def _empty_string_index(table: pa.Table) -> dict[str, list[int]]:
    """Record empty strings, which OOXML reads back as blank cells."""
    found: dict[str, list[int]] = {}
    for name in table.column_names:
        logical = _value_type(table.schema.field(name).type)
        if not _is_text_type(logical):
            continue
        rows = [
            index
            for index, value in enumerate(table.column(name).to_pylist())
            if value == ""
        ]
        if rows:
            found[name] = rows
    return found


def _export_identity(table: pa.Table) -> dict[str, object]:
    run_ids: set[str] = set()
    for name in _RUN_ID_COLUMNS:
        run_ids.update(_distinct_text(table, name))
    return {
        "profile_sha256": _distinct_text(table, _PROFILE_COLUMN),
        "run_ids": sorted(run_ids),
        "table_version": _table_version(table),
    }


def _table_version(table: pa.Table) -> str | None:
    metadata = table.schema.metadata or {}
    stamped = metadata.get(_TABLE_VERSION_METADATA_KEY)
    if isinstance(stamped, bytes) and stamped:
        return stamped.decode("utf-8")
    for name in _VERSION_COLUMNS:
        values = _distinct_text(table, name)
        if len(values) == 1:
            return values[0]
    return None


def _distinct_text(table: pa.Table, column_name: str) -> list[str]:
    if column_name not in table.column_names:
        return []
    values = {
        value
        for value in table.column(column_name).to_pylist()
        if isinstance(value, str) and value
    }
    return sorted(values)


def _write_table_sheet(worksheet: Any, table: pa.Table) -> None:
    headers = list(table.column_names)
    for column_index, header in enumerate(headers, start=1):
        _write_text(worksheet, 1, column_index, header)
    columns = [table.column(name).to_pylist() for name in headers]
    for row_offset, values in enumerate(zip(*columns, strict=True), start=2):
        for column_index, value in enumerate(values, start=1):
            _write_value(worksheet, row_offset, column_index, value)


def _write_manifest_sheet(workbook: Any, manifest: dict[str, object]) -> None:
    payload = json.dumps(
        manifest,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    chunks = _split_text(payload)
    sheet = workbook.create_sheet(XLSX_EXPORT_MANIFEST_SHEET)
    _write_text(sheet, 1, 1, XLSX_TEXT_PARTS_VERSION)
    sheet.cell(2, 1, len(chunks))
    for offset, chunk in enumerate(chunks, start=3):
        _write_text(sheet, offset, 1, chunk)


def _write_value(worksheet: Any, row: int, column: int, value: object) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        worksheet.cell(row, column, value)
        return
    if isinstance(value, int):
        worksheet.cell(row, column, value)
        return
    if isinstance(value, float):
        worksheet.cell(row, column, value)
        return
    _write_text(worksheet, row, column, value if isinstance(value, str) else str(value))


def _write_text(worksheet: Any, row: int, column: int, value: str) -> None:
    if len(value) > _XLSX_MAX_CELL_CHARS:
        raise ValueError("XLSX cell exceeds 32767 characters after splitting")
    cell = worksheet.cell(row, column, value)
    # openpyxl would store a leading "=" as a formula. Explicit text keeps the
    # characters and does not add the CSV apostrophe prefix.
    cell.data_type = "s"


def _force_explicit_text(sheet: Any) -> None:
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"


def _stamp_workbook(workbook: Any) -> None:
    created = datetime(1980, 1, 1)
    workbook.properties.created = created
    workbook.properties.modified = created


def _save_workbook(workbook: Any, output_path: Path) -> None:
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    try:
        workbook.save(temporary)
        temporary.replace(output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
        workbook.close()


def _new_workbook() -> Any:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from exc
    return Workbook()


def _load_workbook(path: str) -> Any:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX export. Install with: pip install openpyxl"
        ) from exc
    return load_workbook(path, data_only=False)


def _read_manifest_workbook(workbook: Any) -> dict[str, object]:
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


def _sheet_records(sheet: Any) -> list[dict[str, object]]:
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
        row: dict[str, object] = {}
        for name in source_columns:
            if name in part_columns:
                row[name] = _join_parts(record, part_columns[name])
            else:
                row[name] = record.get(name)
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


def _table_from_rows(rows: list[dict[str, object]], columns: list[str]) -> pa.Table:
    if not rows:
        return pa.table(
            {name: pa.array([], type=pa.large_string()) for name in columns}
        )
    arrays = [_typed_array([row.get(name) for row in rows]) for name in columns]
    return pa.Table.from_arrays(arrays, names=columns)


def _typed_array(values: list[object]) -> pa.Array:
    present = [value for value in values if value is not None]
    if not present or all(isinstance(value, str) for value in present):
        return pa.array(
            [None if value is None else str(value) for value in values],
            type=pa.large_string(),
        )
    if all(isinstance(value, bool) for value in present):
        return pa.array(values, type=pa.bool_())
    if all(isinstance(value, int) and not isinstance(value, bool) for value in present):
        return pa.array(values, type=pa.int64())
    if all(isinstance(value, float) for value in present):
        return pa.array(values, type=pa.float64())
    return pa.array(
        [None if value is None else str(value) for value in values],
        type=pa.large_string(),
    )


def _require_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"xlsx manifest {label} must be a list of strings")
    return cast(list[str], value)


def _apply_empty_strings(
    records: list[dict[str, object]],
    empty_strings: dict[str, list[int]],
) -> None:
    for column, rows in empty_strings.items():
        for row_index in rows:
            if row_index < 0 or row_index >= len(records):
                raise ValueError("xlsx empty-string marker is out of range")
            if column not in records[row_index]:
                raise ValueError("xlsx empty-string marker column is missing")
            records[row_index][column] = ""


def _require_empty_strings(value: object) -> dict[str, list[int]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("xlsx manifest empty_strings must be an object")
    mapping: dict[str, list[int]] = {}
    for key, rows in value.items():
        if not isinstance(key, str) or not isinstance(rows, list):
            raise ValueError("xlsx manifest empty_strings entries are invalid")
        indexes: list[int] = []
        for row in rows:
            if isinstance(row, bool) or not isinstance(row, int):
                raise ValueError("xlsx manifest empty_strings row must be an integer")
            indexes.append(row)
        mapping[key] = indexes
    return mapping


def _require_part_map(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ValueError("xlsx manifest part_columns must be an object")
    mapping: dict[str, list[str]] = {}
    for key, parts in value.items():
        if not isinstance(key, str):
            raise ValueError("xlsx manifest part column name must be a string")
        mapping[key] = _require_string_list(parts, f"part_columns.{key}")
    return mapping


def _value_type(data_type: pa.DataType) -> pa.DataType:
    if pa.types.is_dictionary(data_type):
        return data_type.value_type
    return data_type


def _is_structured_type(data_type: pa.DataType) -> bool:
    return bool(
        pa.types.is_list(data_type)
        or pa.types.is_large_list(data_type)
        or pa.types.is_fixed_size_list(data_type)
        or pa.types.is_struct(data_type)
        or pa.types.is_map(data_type)
    )


def _is_text_type(data_type: pa.DataType) -> bool:
    return bool(
        pa.types.is_string(data_type)
        or pa.types.is_large_string(data_type)
        or pa.types.is_string_view(data_type)
    )
