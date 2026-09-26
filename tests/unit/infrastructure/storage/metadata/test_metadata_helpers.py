# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for metadata helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pandera.errors import SchemaDefinitionError, SchemaInitError

import bioetl.infrastructure.storage.metadata.metadata_helpers as metadata_helpers


pytestmark = pytest.mark.unit


def test_build_and_validate_metadata_success():
    """Test build_and_validate_metadata function with valid data."""
    key = "test_key"
    value = "test_value"
    result = metadata_helpers.build_and_validate_metadata(key, value)
    assert result == {key: value}


def test_build_and_validate_metadata_failure():
    """Test build_and_validate_metadata function with empty metadata."""
    # Mock the metadata to be empty
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.storage.metadata.metadata_helpers._build_metadata",
            lambda x, y: {},
        )
        with pytest.raises(ValueError, match="Metadata is empty"):
            metadata_helpers.build_and_validate_metadata(
                "test_key",
                "test_value",
            )


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

    result = metadata_helpers.inspect_schema_metadata(_BrokenSchema)

    assert result is not None
    assert result.version == "3.1.0"
    assert result.columns == ()


def test_inspect_schema_metadata_propagates_unknown_errors() -> None:
    class _BrokenSchema:
        @classmethod
        def to_schema(cls) -> object:
            raise RuntimeError("unexpected")

    with pytest.raises(RuntimeError, match="unexpected"):
        metadata_helpers.inspect_schema_metadata(_BrokenSchema)


def test_inspect_schema_metadata_returns_neutral_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metadata_helpers.inspect,
        "getmodule",
        lambda _value: SimpleNamespace(
            __name__="bioetl.domain.contracts.gold.fake_schema"
        ),
    )

    result = metadata_helpers.inspect_schema_metadata(_FakeSchemaWithColumns)

    assert result is not None
    assert result.contract_path == ("src/bioetl/domain/contracts/gold/fake_schema.py")
    assert result.version == "2"
    assert result.validation == "lenient"
    assert tuple(column.name for column in result.columns) == ("entity_id", "score")
    assert result.columns[0].nullable is False
    assert result.columns[1].dtype == "object"


def test_inspect_schema_metadata_none_returns_none() -> None:
    assert metadata_helpers.inspect_schema_metadata(None) is None
