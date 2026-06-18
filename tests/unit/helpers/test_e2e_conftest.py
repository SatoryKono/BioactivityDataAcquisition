"""Unit tests for E2E conftest Delta helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e import conftest as e2e_conftest

pytestmark = pytest.mark.unit


def test_read_delta_records_uses_shared_delta_reader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sentinel_table = object()
    observed: dict[str, object] = {}
    expected = [{"entity_id": "row-1"}]

    def _fake_load_delta_table() -> object:
        def _factory(path: str) -> object:
            observed["path"] = path
            return sentinel_table

        return _factory

    def _fake_load_delta_record_reader() -> object:
        def _reader(table: object, columns: list[str] | None = None) -> list[dict[str, str]]:
            observed["table"] = table
            observed["columns"] = columns
            return expected

        return _reader

    monkeypatch.setattr(e2e_conftest, "_load_delta_table", _fake_load_delta_table)
    monkeypatch.setattr(
        e2e_conftest,
        "_load_delta_record_reader",
        _fake_load_delta_record_reader,
    )

    result = e2e_conftest._read_delta_records(tmp_path / "silver" / "chembl_activity")

    assert result == expected
    assert observed == {
        "path": str(tmp_path / "silver" / "chembl_activity"),
        "table": sentinel_table,
        "columns": None,
    }
