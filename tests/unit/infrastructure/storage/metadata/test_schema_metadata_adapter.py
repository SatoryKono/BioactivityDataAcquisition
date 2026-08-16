"""Tests for the Pandera schema metadata adapter boundary."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pandera.errors import SchemaDefinitionError, SchemaInitError

from bioetl.infrastructure.storage.metadata import schema_metadata_adapter
from bioetl.infrastructure.storage.metadata.schema_metadata_adapter import (
    inspect_schema_metadata,
)

pytestmark = pytest.mark.unit


class _FakeColumn:
    def __init__(self, dtype: object, nullable: bool) -> None:
        self.dtype = dtype
        self.nullable = nullable


class _FakeSchemaInstance:
    columns = {
        "entity_id": _FakeColumn(dtype="pandera.dtypes.String", nullable=False),
        "score": _FakeColumn(dtype=None, nullable=True),
    }


class _FakeSchemaWithColumns:
    class Config:
        version = 2
        strict = False

    @classmethod
    def to_schema(cls) -> _FakeSchemaInstance:
        return _FakeSchemaInstance()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("broken schema"),
        SchemaDefinitionError("invalid definition"),
        SchemaInitError("invalid initialization"),
    ],
)
def test_inspect_schema_metadata_contains_known_construction_errors(
    error: Exception,
) -> None:
    class _BrokenSchema:
        class Config:
            version = "3.1.0"

        @classmethod
        def to_schema(cls) -> object:
            raise error

    result = inspect_schema_metadata(_BrokenSchema)

    assert result is not None
    assert result.version == "3.1.0"
    assert result.columns == ()


def test_inspect_schema_metadata_propagates_unknown_errors() -> None:
    class _BrokenSchema:
        @classmethod
        def to_schema(cls) -> object:
            raise RuntimeError("unexpected")

    with pytest.raises(RuntimeError, match="unexpected"):
        inspect_schema_metadata(_BrokenSchema)


def test_inspect_schema_metadata_returns_neutral_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema_metadata_adapter.inspect,
        "getmodule",
        lambda _value: SimpleNamespace(
            __name__="bioetl.domain.contracts.gold.fake_schema"
        ),
    )

    result = inspect_schema_metadata(_FakeSchemaWithColumns)

    assert result is not None
    assert result.contract_path == ("src/bioetl/domain/contracts/gold/fake_schema.py")
    assert result.version == "2"
    assert result.validation == "lenient"
    assert tuple(column.name for column in result.columns) == ("entity_id", "score")
    assert result.columns[0].nullable is False
    assert result.columns[1].dtype == "object"


def test_inspect_schema_metadata_none_returns_none() -> None:
    assert inspect_schema_metadata(None) is None
