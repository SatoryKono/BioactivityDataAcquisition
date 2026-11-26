"""Split long export text and build the XLSX text-part manifest."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa

from bioetl.domain.serialization import serialize_to_json
from bioetl.infrastructure.export.xlsx_workbook import (
    XLSX_MAX_CELL_CHARS,
    XLSX_TEXT_PARTS_VERSION,
    is_structured_type,
    is_text_type,
    new_xlsx_workbook,
    save_xlsx_workbook,
    split_xlsx_text,
    stamp_xlsx_workbook,
    value_type,
    write_xlsx_manifest_sheet,
    write_xlsx_table_sheet,
)

__all__ = ["XLSX_TEXT_PARTS_VERSION", "write_arrow_xlsx"]

_DATA_SHEET_NAME = "Sheet1"
_PART_SUFFIX = "__bioetl_part_"
_TABLE_VERSION_METADATA_KEY = b"bioetl.table_version"
_XLSX_MAX_COLUMNS = 16384
_XLSX_MAX_ROWS = 1048576
_RUN_ID_COLUMNS = ("_run_id", "run_id")
_PROFILE_COLUMN = "target_class_profile_sha256"
_VERSION_COLUMNS = ("table_version", "delta_version")


def write_arrow_xlsx(
    table: pa.Table,
    output_path: Path,
    *,
    table_name: str,
    layer: str,
) -> Path:
    """Write an Arrow table with canonical structured values and text parts.

    Text longer than 32767 characters is split. The first part keeps the
    source column name. Later parts use ``<column>__bioetl_part_0002`` and
    the following numbers. ``restore_xlsx_table`` joins them.
    """
    if table.num_rows > _XLSX_MAX_ROWS - 1:
        raise ValueError("XLSX export exceeds 1048576 rows")
    table = _dedupe_columns(table)
    canonical = _canonicalize_structured_columns(table)
    expanded, part_columns = _expand_long_text(canonical)
    manifest = _export_manifest(
        canonical,
        table_name=table_name,
        layer=layer,
        part_columns=part_columns,
        empty_strings=_empty_string_index(expanded),
    )
    workbook = new_xlsx_workbook()
    worksheet = workbook.active
    worksheet.title = _DATA_SHEET_NAME
    numeric_text_columns = write_xlsx_table_sheet(worksheet, expanded)
    if numeric_text_columns:
        manifest["numeric_text_columns"] = numeric_text_columns
    write_xlsx_manifest_sheet(workbook, manifest)
    stamp_xlsx_workbook(workbook)
    save_xlsx_workbook(workbook, output_path)
    return output_path


def _canonicalize_structured_columns(table: pa.Table) -> pa.Table:
    """Serialize list, struct, and map columns to canonical JSON strings."""
    arrays: list[pa.Array | pa.ChunkedArray] = []
    fields: list[pa.Field] = []
    changed = False
    for index, field in enumerate(table.schema):
        logical = value_type(field.type)
        if not is_structured_type(logical):
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
        logical = value_type(field.type)
        column = table.column(index)
        if not is_text_type(logical):
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
        None if value is None else split_xlsx_text(str(value))
        for value in column.to_pylist()
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
        "column_types": [_stored_type_name(field.type) for field in table.schema],
        "data_sheet": _DATA_SHEET_NAME,
        "empty_strings": empty_strings,
        "identity": _export_identity(table),
        "layer": layer,
        "max_cell_chars": XLSX_MAX_CELL_CHARS,
        "part_columns": part_columns,
        "row_count": table.num_rows,
        "schema_version": XLSX_TEXT_PARTS_VERSION,
        "source_columns": list(table.column_names),
        "table_name": table_name,
    }


def _dedupe_columns(table: pa.Table) -> pa.Table:
    """Keep the first occurrence of each column name."""
    seen: set[str] = set()
    indexes: list[int] = []
    for index, name in enumerate(table.column_names):
        if name in seen:
            continue
        seen.add(name)
        indexes.append(index)
    if len(indexes) == table.num_columns:
        return table
    return table.select(indexes)


def _stored_type_name(data_type: pa.DataType) -> str:
    """Return the Arrow type name written into the workbook."""
    logical = value_type(data_type)
    if pa.types.is_boolean(logical) or pa.types.is_integer(logical):
        return str(logical)
    if pa.types.is_floating(logical):
        return str(logical)
    if is_text_type(logical):
        return str(logical)
    return "large_string"


def _empty_string_index(table: pa.Table) -> dict[str, list[int]]:
    """Record empty strings, which OOXML reads back as blank cells."""
    found: dict[str, list[int]] = {}
    for index, name in enumerate(table.column_names):
        logical = value_type(table.schema.field(index).type)
        if not is_text_type(logical):
            continue
        rows = [
            row_index
            for row_index, value in enumerate(table.column(index).to_pylist())
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
