"""Unit tests for Delta table read helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bioetl.infrastructure.storage.delta import table_ops

pytestmark = pytest.mark.unit


class _FakeBatch:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_pylist(self) -> list[dict[str, object]]:
        return list(self._rows)


class _FakeScanner:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_reader(self) -> list[_FakeBatch]:
        return [_FakeBatch(self._rows)]


class _FakeDataset:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.requested_columns: list[str] | None = None

    def scanner(self, *, columns: list[str] | None = None) -> _FakeScanner:
        self.requested_columns = columns
        return _FakeScanner(self._rows)


class _FakeArrowTable:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_pylist(self) -> list[dict[str, object]]:
        return list(self._rows)


def test_read_delta_records_uses_dataset_scanner_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        table_ops,
        "_can_use_pyarrow_dataset_scanner",
        lambda: True,
    )
    rows = [{"entity_id": "row-1"}]
    dataset = _FakeDataset(rows)

    class _FakeTable:
        def to_pyarrow_dataset(self) -> _FakeDataset:
            return dataset

        def to_pyarrow_table(self, *, columns: list[str] | None = None) -> _FakeArrowTable:
            raise AssertionError("fallback path should not be used")

    assert table_ops.read_delta_records(_FakeTable(), columns=["entity_id"]) == rows
    assert dataset.requested_columns == ["entity_id"]


def test_read_delta_records_skips_dataset_scanner_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        table_ops,
        "_can_use_pyarrow_dataset_scanner",
        lambda: False,
    )
    rows = [{"entity_id": "row-1"}]
    observed: dict[str, object] = {}

    class _FakeTable:
        def to_pyarrow_dataset(self) -> _FakeDataset:
            raise AssertionError("Windows path must not import dataset scanner")

        def to_pyarrow_table(self, *, columns: list[str] | None = None) -> _FakeArrowTable:
            observed["columns"] = columns
            return _FakeArrowTable(rows)

    assert table_ops.read_delta_records(_FakeTable(), columns=["entity_id"]) == rows
    assert observed == {"columns": ["entity_id"]}


def test_resolve_delta_table_path_uses_pathlib_join() -> None:
    resolved = table_ops.resolve_delta_table_path(
        base_path="/tmp/output/silver",
        table_name="chembl.target",
        flat_structure=False,
    )
    assert resolved == (Path("/tmp/output/silver") / "chembl" / "target").as_posix()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path semantics")
def test_resolve_delta_table_path_normalizes_windows_base_path() -> None:
    resolved = table_ops.resolve_delta_table_path(
        base_path=r"C:\data\output\silver",
        table_name="chembl.target",
        flat_structure=False,
    )
    assert resolved == (Path(r"C:\data\output\silver") / "chembl" / "target").as_posix()
    assert "\\" not in resolved


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path semantics")
def test_normalize_delta_filesystem_path_uses_posix_style() -> None:
    normalized = table_ops.normalize_delta_filesystem_path(
        r"C:\data\output\silver\chembl\target"
    )
    assert normalized == (
        Path(r"C:\data\output\silver\chembl\target").resolve().as_posix()
    )
    assert "\\" not in normalized
