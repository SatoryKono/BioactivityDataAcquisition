"""Tests for retention Delta helper seams."""

from __future__ import annotations

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
            def to_arrow(self) -> str:
                return "arrow-schema"

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
        "schema": "arrow-schema",
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
