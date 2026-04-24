"""Integration tests for BaseDeltaWriter filesystem behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter

pytestmark = pytest.mark.integration


def _make_writer(base_path: Path) -> BaseDeltaWriter:
    return BaseDeltaWriter(base_path=base_path, logger=MagicMock())


def test_clear_specific_table(tmp_path: Path) -> None:
    """Clear should respect dry-run and remove the targeted Delta table."""
    table_dir = tmp_path / "test_table"
    delta_log = table_dir / "_delta_log"
    delta_log.mkdir(parents=True)
    (delta_log / "00000.json").touch()

    writer = _make_writer(tmp_path)

    result = writer.clear(table_name="test_table", dry_run=True)
    assert result == 1
    assert table_dir.exists()

    result = writer.clear(table_name="test_table", dry_run=False)
    assert result == 1
    assert not table_dir.exists()


def test_clear_all_tables(tmp_path: Path) -> None:
    """Clear should remove only directories that look like Delta tables."""
    for name in ["table1", "table2", "not_a_table"]:
        table_dir = tmp_path / name
        table_dir.mkdir()
        if name != "not_a_table":
            (table_dir / "_delta_log").mkdir()

    writer = _make_writer(tmp_path)

    result = writer.clear(dry_run=False)

    assert result == 2
    assert not (tmp_path / "table1").exists()
    assert not (tmp_path / "table2").exists()
    assert (tmp_path / "not_a_table").exists()
