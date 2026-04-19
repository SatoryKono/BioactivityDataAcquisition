"""Domain-pure tests for schema metadata extraction rules."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.domain.services.schema_metadata_extractor import extract_schema_metadata


class _FakeColumn:
    def __init__(self, dtype: object, nullable: bool) -> None:
        self.dtype = dtype
        self.nullable = nullable


class _FakeSchemaInstance:
    columns = {
        "entity_id": _FakeColumn(dtype="pandera.dtypes.String", nullable=False),
        "score": _FakeColumn(dtype="pandera.dtypes.Float64", nullable=True),
    }


class _FakeSchemaWithColumns:
    class Config:
        version = 2
        strict = False

    @classmethod
    def to_schema(cls) -> _FakeSchemaInstance:
        return _FakeSchemaInstance()


class _FakeSchemaExtractionError:
    class Config:
        version = "3.1.0"
        strict = True

    @classmethod
    def to_schema(cls) -> _FakeSchemaInstance:
        raise ValueError("broken schema")


def test_extract_schema_metadata_none_returns_defaults() -> None:
    metadata = extract_schema_metadata(None)
    assert metadata.contract_path is None
    assert metadata.version == "1.0"
    assert metadata.validation == "strict"
    assert metadata.columns == []


def test_extract_schema_metadata_from_schema_with_columns() -> None:
    metadata = extract_schema_metadata(_FakeSchemaWithColumns)

    assert metadata.version == "2"
    assert metadata.validation == "lenient"
    assert len(metadata.columns) == 2
    assert metadata.columns[0].name == "entity_id"
    assert metadata.columns[0].type == "String"
    assert metadata.columns[0].nullable is False
    assert metadata.columns[1].name == "score"
    assert metadata.columns[1].type == "Float64"
    assert metadata.columns[1].nullable is True


def test_extract_schema_metadata_handles_schema_extraction_error() -> None:
    metadata = extract_schema_metadata(_FakeSchemaExtractionError)
    assert metadata.version == "3.1.0"
    assert metadata.validation == "strict"
    assert metadata.columns == []


def test_extract_schema_metadata_contract_path_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.domain.services.schema_metadata_extractor as extractor_module

    fake_module = SimpleNamespace(
        __file__="/workspace/src/bioetl/domain/contracts/gold/fake_schema.py"
    )
    monkeypatch.setattr(extractor_module.inspect, "getmodule", lambda _: fake_module)

    metadata = extract_schema_metadata(_FakeSchemaWithColumns)
    assert metadata.contract_path == "src/bioetl/domain/contracts/gold/fake_schema.py"
