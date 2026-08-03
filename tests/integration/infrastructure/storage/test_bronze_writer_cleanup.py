# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for BronzeWriter cleanup behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration


def _make_writer(base_path: Path) -> BronzeWriter:
    return BronzeWriter(
        base_path=base_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
    )


def test_find_old_date_dirs_finds_old_directories(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    entity_path = tmp_path / "chembl" / "activity"

    old_date = entity_path / "2024-01-01"
    old_date.mkdir(parents=True)
    (old_date / "batch.jsonl.zst").touch()

    newer_date = entity_path / "2024-06-01"
    newer_date.mkdir(parents=True)
    (newer_date / "batch.jsonl.zst").touch()

    result = writer._find_old_date_dirs("2024-03-01")

    assert result == [old_date]


def test_find_old_date_dirs_ignores_non_date_directories(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    entity_path = tmp_path / "chembl" / "activity"

    (entity_path / "not-a-date").mkdir(parents=True)
    date_dir = entity_path / "2024-01-01"
    date_dir.mkdir(parents=True)

    result = writer._find_old_date_dirs("2024-12-01")

    assert len(result) == 1
    assert result[0].name == "2024-01-01"


@pytest.mark.asyncio
async def test_cleanup_old_files_removes_old_data(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    old_date = tmp_path / "chembl" / "activity" / "2024-01-01"
    old_date.mkdir(parents=True)
    old_file = old_date / "batch.jsonl.zst"
    old_file.write_bytes(b"test data")

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff)

    assert result["files_removed"] == 1
    assert result["bytes_freed"] > 0
    assert result["directories_removed"] == 1
    assert not old_date.exists()


@pytest.mark.asyncio
async def test_cleanup_old_files_dry_run(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    old_date = tmp_path / "chembl" / "activity" / "2024-01-01"
    old_date.mkdir(parents=True)
    old_file = old_date / "batch.jsonl.zst"
    old_file.write_bytes(b"test data")

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff, dry_run=True)

    assert result["files_removed"] == 1
    assert result["directories_removed"] == 1
    assert old_file.exists()
    assert old_date.exists()


@pytest.mark.asyncio
async def test_cleanup_old_files_preserves_recent_data(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    recent_date = tmp_path / "chembl" / "activity" / "2024-12-01"
    recent_date.mkdir(parents=True)
    recent_file = recent_date / "batch.jsonl.zst"
    recent_file.write_bytes(b"test data")

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff)

    assert result["files_removed"] == 0
    assert result["directories_removed"] == 0
    assert recent_file.exists()


@pytest.mark.asyncio
async def test_cleanup_old_files_multiple_providers(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)

    for provider in ["chembl", "pubchem"]:
        for entity in ["activity", "compound"]:
            old_date = tmp_path / provider / entity / "2024-01-01"
            old_date.mkdir(parents=True)
            (old_date / "batch.jsonl.zst").write_bytes(b"data")

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff)

    assert result["files_removed"] == 4
    assert result["directories_removed"] == 4
