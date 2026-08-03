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
"""Tests for retention Delta helper seams."""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.domain.exceptions import TableNotFoundError
from bioetl.infrastructure.storage.support import retention_delta

pytestmark = pytest.mark.unit


class _FakeDeltaTable:
    def version(self) -> int:
        return 7

    def file_uris(self) -> list[str]:
        return ["file-a.parquet", "file-b.parquet"]

    def schema(self) -> object:
        class _Schema:
            def to_arrow(self) -> pa.Schema:
                return pa.schema([("id", pa.string())])

        return _Schema()

    def metadata(self) -> dict[str, str]:
        return {"name": "chembl.activity"}


def test_retention_delta_helpers_build_paths_and_table_info(monkeypatch) -> None:
    table = _FakeDeltaTable()
    monkeypatch.setattr(retention_delta, "DeltaTable", lambda path: table)

    assert (
        retention_delta.get_table_path("/data/silver", "chembl.activity")
        == "/data/silver/chembl/activity"
    )
    assert retention_delta.load_delta_table("/data/silver/chembl/activity") is table
    assert retention_delta.build_table_info(table) == {
        "version": 7,
        "num_files": 2,
        "schema": pa.schema([("id", pa.string())]),
        "metadata": {"name": "chembl.activity"},
    }


def test_load_delta_table_translates_missing_table(monkeypatch) -> None:
    class _MissingDeltaTableError(Exception):
        pass

    def raise_missing(_: str) -> object:
        raise _MissingDeltaTableError("missing")

    monkeypatch.setattr(
        retention_delta,
        "DeltaTableNotFoundError",
        _MissingDeltaTableError,
    )
    monkeypatch.setattr(retention_delta, "DeltaTable", raise_missing)

    with pytest.raises(TableNotFoundError):
        retention_delta.load_delta_table("/data/missing")
