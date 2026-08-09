"""Owner tests for typed Arrow schema wrappers (PD7-4 / zero-import triage)."""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.infrastructure import arrow_typed

pytestmark = pytest.mark.unit


def test_arrow_typed_field_and_schema_round_trip() -> None:
    field = arrow_typed.field("id", arrow_typed.string(), nullable=False)
    assert isinstance(field, pa.Field)
    assert field.name == "id"
    assert field.nullable is False

    schema = arrow_typed.schema(
        [
            field,
            arrow_typed.field("score", arrow_typed.float64()),
            arrow_typed.field("count", arrow_typed.int64()),
            arrow_typed.field("flag", arrow_typed.bool_()),
        ]
    )
    assert isinstance(schema, pa.Schema)
    assert schema.names == ["id", "score", "count", "flag"]


def test_arrow_typed_struct_and_list_builders() -> None:
    nested = arrow_typed.struct(
        [
            arrow_typed.field("k", arrow_typed.string()),
            arrow_typed.field("v", arrow_typed.int32()),
        ]
    )
    listed = arrow_typed.list_(arrow_typed.string())
    assert isinstance(nested, pa.DataType)
    assert isinstance(listed, pa.DataType)

def test_arrow_typed_metadata() -> None:
    meta = {"key": "value"}
    field = arrow_typed.field("id", arrow_typed.string(), metadata=meta)
    assert isinstance(field, pa.Field)
    assert field.metadata == {b"key": b"value"}

    schema = arrow_typed.schema([field], metadata=meta)
    assert isinstance(schema, pa.Schema)
    assert schema.metadata == {b"key": b"value"}


def test_arrow_typed_types() -> None:
    assert isinstance(arrow_typed.null(), pa.DataType)
    assert isinstance(arrow_typed.timestamp("us"), pa.DataType)
    assert isinstance(arrow_typed.timestamp("us", tz="UTC"), pa.DataType)


def test_arrow_typed_as_data_type() -> None:
    dt = arrow_typed.as_data_type(pa.string())
    assert isinstance(dt, pa.DataType)
