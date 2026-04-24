"""Integration tests for SilverWriter filesystem behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = pytest.mark.integration


class _ConcreteMaintMixin(SilverWriterMaintenanceMixin):
    """Concrete maintenance mixin host backed by a real path root."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def get_table_path(self, name: str) -> Path:
        return self._base_path / name


def test_clear_specific_table(noop_logger, tmp_path: Path) -> None:
    """Clear should remove the targeted Delta table directory."""
    table_path = tmp_path / "chembl" / "activity"
    delta_log = table_path / "_delta_log"
    delta_log.mkdir(parents=True)
    (table_path / "part-00000.parquet").touch()

    writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
    result = writer.clear(table_name="chembl.activity")

    assert result == 1
    assert not table_path.exists()


def test_clear_specific_table_dry_run(noop_logger, tmp_path: Path) -> None:
    """Dry-run clear should report without deleting files."""
    table_path = tmp_path / "chembl" / "activity"
    (table_path / "_delta_log").mkdir(parents=True)

    writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
    result = writer.clear(table_name="chembl.activity", dry_run=True)

    assert result == 1
    assert table_path.exists()


def test_clear_all_tables(noop_logger, tmp_path: Path) -> None:
    """Clear should remove every Delta-style table rooted at base_path."""
    for name in ["table1", "table2", "table3"]:
        (tmp_path / name / "_delta_log").mkdir(parents=True)

    writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
    result = writer.clear()

    assert result == 3
    assert not (tmp_path / "table1").exists()
    assert not (tmp_path / "table2").exists()
    assert not (tmp_path / "table3").exists()


def test_clear_ignores_non_delta_directories(noop_logger, tmp_path: Path) -> None:
    """Clear should ignore directories without Delta log structure."""
    (tmp_path / "delta_table" / "_delta_log").mkdir(parents=True)
    non_delta = tmp_path / "non_delta"
    non_delta.mkdir()
    (non_delta / "some_file.txt").touch()

    writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
    result = writer.clear()

    assert result == 1
    assert not (tmp_path / "delta_table").exists()
    assert non_delta.exists()


def test_preview_cleanup_existing_table(tmp_path: Path) -> None:
    """Preview should count files under an existing table directory."""
    mixin = _ConcreteMaintMixin(tmp_path)
    table_path = tmp_path / "test_table"
    table_path.mkdir(parents=True)
    (table_path / "part-001.parquet").write_bytes(b"data1")
    (table_path / "part-002.parquet").write_bytes(b"data2")
    (table_path / "_delta_log").mkdir()
    (table_path / "_delta_log" / "000.json").write_text("{}", encoding="utf-8")

    result = mixin.preview_cleanup("test_table")

    assert result["exists"] is True
    assert result["path"] == str(table_path)
    assert result["file_count"] == 3


def test_preview_cleanup_nonexistent_table(tmp_path: Path) -> None:
    """Preview should report a nonexistent table without file mutations."""
    mixin = _ConcreteMaintMixin(tmp_path)

    result = mixin.preview_cleanup("nonexistent_table")

    assert result["exists"] is False
    assert result["file_count"] == 0
    assert isinstance(result["path"], str)


def test_preview_cleanup_empty_table(tmp_path: Path) -> None:
    """Preview should report zero files for an existing but empty table directory."""
    mixin = _ConcreteMaintMixin(tmp_path)
    table_path = tmp_path / "empty_table"
    table_path.mkdir(parents=True)

    result = mixin.preview_cleanup("empty_table")

    assert result["exists"] is True
    assert result["file_count"] == 0
