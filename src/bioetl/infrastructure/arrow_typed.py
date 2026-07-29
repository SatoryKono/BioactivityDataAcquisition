"""Typed thin wrappers around pyarrow schema primitives (PD7-4).

PyArrow's runtime API is intentionally dynamic; under basedpyright many
``pa.field`` / ``pa.string`` call sites surface as unknown member/types.
These wrappers pin return types so Silver schema modules stay
quiet without bulk ``# type: ignore`` or product Port weakening.
"""

from __future__ import annotations

from typing import Any, cast

import pyarrow as pa

__all__ = [
    "bool_",
    "field",
    "float64",
    "int32",
    "int64",
    "list_",
    "null",
    "schema",
    "string",
    "struct",
    "timestamp",
]


def field(
    name: str,
    type_: pa.DataType,
    nullable: bool = True,
    *,
    metadata: dict[str, str] | None = None,
) -> pa.Field:
    """Return a ``pa.Field`` with a known return type for static checkers."""
    if metadata is None:
        return cast(pa.Field, pa.field(name, type_, nullable=nullable))
    return cast(
        pa.Field,
        pa.field(name, type_, nullable=nullable, metadata=metadata),
    )


def string() -> pa.DataType:
    """Return Arrow string type with known static type."""
    return cast(pa.DataType, pa.string())


def int64() -> pa.DataType:
    return cast(pa.DataType, pa.int64())


def int32() -> pa.DataType:
    return cast(pa.DataType, pa.int32())


def float64() -> pa.DataType:
    return cast(pa.DataType, pa.float64())


def bool_() -> pa.DataType:
    return cast(pa.DataType, pa.bool_())


def null() -> pa.DataType:
    return cast(pa.DataType, pa.null())


def timestamp(unit: str = "us", tz: str | None = None) -> pa.DataType:
    if tz is None:
        return cast(pa.DataType, pa.timestamp(unit))
    return cast(pa.DataType, pa.timestamp(unit, tz=tz))


def list_(value_type: pa.DataType) -> pa.DataType:
    return cast(pa.DataType, pa.list_(value_type))


def struct(fields: list[pa.Field]) -> pa.DataType:
    return cast(pa.DataType, pa.struct(fields))


def schema(fields: list[pa.Field], *, metadata: dict[str, str] | None = None) -> pa.Schema:
    if metadata is None:
        return cast(pa.Schema, pa.schema(fields))
    return cast(pa.Schema, pa.schema(fields, metadata=metadata))


def as_data_type(value: Any) -> pa.DataType:  # Any: dynamic Arrow type boundary
    """Boundary cast for rare dynamic Arrow type values."""
    return cast(pa.DataType, value)
