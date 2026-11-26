"""Restore Arrow values from an XLSX text-part export."""

from __future__ import annotations

from typing import cast

import pyarrow as pa


def value_type(data_type: pa.DataType) -> pa.DataType:
    """Unwrap dictionary encoding before a logical type check."""
    if pa.types.is_dictionary(data_type):
        return data_type.value_type
    return data_type


def is_structured_type(data_type: pa.DataType) -> bool:
    """Return whether a column is a list, struct, or map."""
    return bool(
        pa.types.is_list(data_type)
        or pa.types.is_large_list(data_type)
        or pa.types.is_fixed_size_list(data_type)
        or pa.types.is_struct(data_type)
        or pa.types.is_map(data_type)
    )


def is_text_type(data_type: pa.DataType) -> bool:
    """Return whether a column is stored as text."""
    return bool(
        pa.types.is_string(data_type)
        or pa.types.is_large_string(data_type)
        or pa.types.is_string_view(data_type)
    )


def table_from_xlsx_rows(
    rows: list[dict[str, object]],
    columns: list[str],
    column_types: list[str] | None,
    *,
    numeric_text_columns: set[str],
) -> pa.Table:
    if column_types is not None and len(column_types) != len(columns):
        raise ValueError("xlsx manifest column_types length does not match columns")
    if numeric_text_columns and column_types is None:
        raise ValueError("xlsx numeric text requires declared column types")
    if not rows:
        types = column_types or ["large_string"] * len(columns)
        return pa.table(
            {
                name: pa.array([], type=_export_type(type_name))
                for name, type_name in zip(columns, types, strict=True)
            }
        )
    arrays = [
        _typed_array(
            [row.get(name) for row in rows],
            None if column_types is None else column_types[index],
            allow_numeric_text=name in numeric_text_columns,
        )
        for index, name in enumerate(columns)
    ]
    return pa.Table.from_arrays(arrays, names=columns)


def _typed_array(
    values: list[object], type_name: str | None, *, allow_numeric_text: bool
) -> pa.Array:
    if type_name is None:
        return _inferred_array(values)
    return _array_for_declared_type(
        values, _export_type(type_name), allow_numeric_text=allow_numeric_text
    )


def _inferred_array(values: list[object]) -> pa.Array:
    present = [value for value in values if value is not None]
    if _is_number_column(present):
        return _inferred_number_array(values, present)
    if _all_text(present):
        return _text_array(values)
    if all(isinstance(value, bool) for value in present):
        return pa.array(values, type=pa.bool_())
    return _text_array(values)


def _inferred_number_array(values: list[object], present: list[object]) -> pa.Array:
    if any(isinstance(value, float) for value in present):
        return pa.array(_as_floats(values), type=pa.float64())
    return pa.array(values, type=pa.int64())


def _all_text(values: list[object]) -> bool:
    return not values or all(isinstance(value, str) for value in values)


def _text_array(values: list[object]) -> pa.Array:
    return pa.array(
        [None if value is None else str(value) for value in values],
        type=pa.large_string(),
    )


def _array_for_declared_type(
    values: list[object], data_type: pa.DataType, *, allow_numeric_text: bool
) -> pa.Array:
    if pa.types.is_floating(data_type):
        return pa.array(
            _as_floats(values, allow_numeric_text=allow_numeric_text), type=data_type
        )
    if pa.types.is_integer(data_type):
        return pa.array(
            _as_ints(values, allow_numeric_text=allow_numeric_text), type=data_type
        )
    if allow_numeric_text:
        raise ValueError(
            "xlsx numeric text requires an integer or floating-point column"
        )
    if pa.types.is_boolean(data_type):
        return pa.array(values, type=data_type)
    if is_text_type(data_type):
        return pa.array(
            [None if value is None else str(value) for value in values],
            type=data_type,
        )
    return _text_array(values)


def _is_number_column(values: list[object]) -> bool:
    return bool(values) and all(_is_number(value) for value in values)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_floats(
    values: list[object], *, allow_numeric_text: bool = False
) -> list[float | None]:
    converted: list[float | None] = []
    for value in values:
        if value is None:
            converted.append(None)
            continue
        if allow_numeric_text and isinstance(value, str):
            converted.append(float(value))
            continue
        if not _is_number(value):
            raise ValueError("xlsx numeric value is not a number")
        converted.append(float(cast(int | float, value)))
    return converted


def _as_ints(
    values: list[object], *, allow_numeric_text: bool = False
) -> list[int | None]:
    converted: list[int | None] = []
    for value in values:
        if value is None:
            converted.append(None)
            continue
        if allow_numeric_text and isinstance(value, str):
            converted.append(int(value))
            continue
        if not _is_number(value):
            raise ValueError("xlsx integer value is not an integer")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("xlsx integer value has a fractional part")
        converted.append(int(cast(int | float, value)))
    return converted


def _export_type(type_name: str) -> pa.DataType:
    try:
        return pa.type_for_alias(type_name)
    except (ValueError, pa.ArrowInvalid):
        return pa.large_string()


def _optional_string_list(value: object) -> list[str] | None:
    if value is None:
        return None
    return _require_string_list(value, "column_types")


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
        mapping[key] = [_require_row_index(row) for row in rows]
    return mapping


def _require_row_index(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("xlsx manifest empty_strings row must be an integer")
    return value


def _require_part_map(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ValueError("xlsx manifest part_columns must be an object")
    mapping: dict[str, list[str]] = {}
    for key, parts in value.items():
        if not isinstance(key, str):
            raise ValueError("xlsx manifest part column name must be a string")
        mapping[key] = _require_string_list(parts, f"part_columns.{key}")
    return mapping
