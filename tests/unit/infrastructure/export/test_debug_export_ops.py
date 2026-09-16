"""Unit tests for debug-export workbook and fingerprint helpers."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.export.debug_export_ops import (
    acquire_worksheet,
    chunk_table_rows,
    compute_pack_hash,
    compute_tables_hash,
    fingerprint_artifact,
    sheet_name_for_chunk,
    write_debug_xlsx,
    write_sheet_rows,
)

pytestmark = pytest.mark.unit


def test_chunk_table_rows_reserves_header_and_handles_empty_input() -> None:
    rows = tuple({"id": index} for index in range(5))
    assert chunk_table_rows(rows, max_rows_per_sheet=3) == [
        ({"id": 0}, {"id": 1}),
        ({"id": 2}, {"id": 3}),
        ({"id": 4},),
    ]
    assert chunk_table_rows((), max_rows_per_sheet=0) == [()]


def test_sheet_name_for_chunk_is_stable_and_excel_bounded() -> None:
    long_name = "x" * 40
    assert sheet_name_for_chunk(long_name, 1, 1) == "x" * 31
    chunked = sheet_name_for_chunk(long_name, 2, 3)
    assert len(chunked) == 31
    assert chunked.endswith("_0002")


def test_write_sheet_rows_sets_navigation_and_normalizes_values() -> None:
    sheet = MagicMock()
    sheet.dimensions = "A1:B2"
    sheet.auto_filter = SimpleNamespace(ref=None)

    write_sheet_rows(
        sheet,
        headers=["id", "payload"],
        chunk=({"id": 1, "payload": {"b": 2, "a": 1}},),
    )

    assert sheet.freeze_panes == "A2"
    assert sheet.append.call_args_list[0].args[0] == ["id", "payload"]
    assert sheet.append.call_args_list[1].args[0] == [1, '{"a": 1, "b": 2}']
    assert sheet.auto_filter.ref == "A1:B2"


def test_acquire_worksheet_reuses_first_sheet_then_creates_named_sheets() -> None:
    active = SimpleNamespace(title="Sheet")
    book = MagicMock()
    book.active = active
    created = MagicMock()
    book.create_sheet.return_value = created

    worksheet, first_sheet = acquire_worksheet(
        book, sheet_name="first", first_sheet=True
    )
    assert worksheet is active
    assert active.title == "first"
    assert first_sheet is False

    worksheet, first_sheet = acquire_worksheet(
        book, sheet_name="second", first_sheet=False
    )
    assert worksheet is created
    assert first_sheet is False
    book.create_sheet.assert_called_once_with(title="second")


def test_acquire_worksheet_rejects_workbook_without_active_sheet() -> None:
    book = MagicMock()
    book.active = None
    with pytest.raises(RuntimeError, match="active worksheet"):
        acquire_worksheet(book, sheet_name="first", first_sheet=True)


def test_write_debug_xlsx_builds_deterministic_chunked_workbook(tmp_path: Path) -> None:
    book = MagicMock()
    book.properties = SimpleNamespace(created=None, modified=None)
    book.active = MagicMock()
    book.active.auto_filter = SimpleNamespace(ref=None)
    book.active.dimensions = "A1:A2"
    extra = MagicMock()
    extra.auto_filter = SimpleNamespace(ref=None)
    extra.dimensions = "A1:A2"
    book.create_sheet.return_value = extra
    output = tmp_path / "debug.xlsx"

    openpyxl = SimpleNamespace(Workbook=MagicMock(return_value=book))
    with patch.dict(sys.modules, {"openpyxl": openpyxl}):
        write_debug_xlsx(
            output,
            {"records": ({"id": 1}, {"id": 2}, {"id": 3})},
            max_rows_per_sheet=3,
        )

    assert book.properties.created == book.properties.modified
    assert book.active.title == "records_0001"
    book.create_sheet.assert_called_once_with(title="records_0002")
    book.save.assert_called_once_with(output)


def test_fingerprint_artifact_supports_relative_path_and_optional_hash(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "nested" / "artifact.txt"
    artifact.parent.mkdir()
    artifact.write_bytes(b"payload")

    fingerprint = fingerprint_artifact(artifact, root_path=tmp_path)
    assert fingerprint == {
        "path": str(Path("nested") / "artifact.txt"),
        "size_bytes": 7,
        "sha256": hashlib.sha256(b"payload").hexdigest(),
    }
    absolute = fingerprint_artifact(artifact, include_content_hash=False)
    assert absolute == {"path": str(artifact), "size_bytes": 7}


def test_pack_and_table_hashes_are_canonical_and_timestamp_independent() -> None:
    artifacts = [{"path": "b", "size_bytes": 2}, {"path": "a", "size_bytes": 1}]
    expected_pack = hashlib.sha256(
        json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert compute_pack_hash(artifacts) == expected_pack

    left = {"records": ({"id": 1, "created_at": "old", "payload": [2, 1]},)}
    right = {"records": ({"id": 1, "created_at": "new", "payload": [2, 1]},)}
    assert compute_tables_hash(left) == compute_tables_hash(right)
