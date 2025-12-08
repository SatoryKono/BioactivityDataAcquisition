"""Helpers to derive pipeline field configs from Pandera schemas."""

from __future__ import annotations

from typing import Any

import pandera as pa

_DEFAULT_FILTERABLE = False


def _map_dtype_to_field_type(dtype: Any) -> str:
    """Map Pandera/NumPy dtype representation to config-friendly type name."""

    dtype_str = str(dtype).lower()
    if "int" in dtype_str:
        return "integer"
    if "float" in dtype_str or "double" in dtype_str:
        return "number"
    if "bool" in dtype_str:
        return "boolean"
    if "object" in dtype_str:
        return "object"
    return "string"


def build_field_configs_from_schema(
    schema: type[pa.DataFrameModel] | pa.DataFrameSchema,
) -> list[dict[str, Any]]:
    """Convert Pandera schema definition to list of field descriptors."""

    df_schema = schema.to_schema() if hasattr(schema, "to_schema") else schema
    columns = getattr(df_schema, "columns", None)
    if columns is None:
        raise TypeError("Schema must define columns attribute")

    fields: list[dict[str, Any]] = []
    for name, column in columns.items():
        fields.append(
            {
                "name": name,
                "data_type": _map_dtype_to_field_type(column.dtype),
                "is_nullable": bool(column.nullable),
                "is_filterable": _DEFAULT_FILTERABLE,
                "description": column.description or "",
            }
        )
    return fields


__all__ = ["build_field_configs_from_schema"]
