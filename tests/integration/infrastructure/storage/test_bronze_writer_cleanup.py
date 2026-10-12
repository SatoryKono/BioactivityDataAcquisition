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

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration
_APPLY_POSIX = pytest.mark.skipif(
    os.name == "nt", reason="Windows destructive cleanup is fail-closed (NOT_VERIFIED)"
)
_ARTIFACT = "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"


def _write_pair(date_dir: Path, data: bytes = b"test data") -> Path:
    payload = date_dir / _ARTIFACT
    payload.write_bytes(data)
    (date_dir / f"{_ARTIFACT}.meta.json").write_bytes(b"{}")
    return payload


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
    (
        old_date / "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
    ).touch()

    newer_date = entity_path / "2024-06-01"
    newer_date.mkdir(parents=True)
    (
        newer_date / "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
    ).touch()

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
@_APPLY_POSIX
async def test_cleanup_old_files_removes_old_data(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    old_date = tmp_path / "chembl" / "activity" / "2024-01-01"
    old_date.mkdir(parents=True)
    old_file = _write_pair(old_date)

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff)

    assert result["files_removed"] == 2
    assert result["bytes_freed"] > 0
    assert result["directories_removed"] == 1
    assert not old_date.exists()


@pytest.mark.asyncio
async def test_cleanup_old_files_dry_run(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    old_date = tmp_path / "chembl" / "activity" / "2024-01-01"
    old_date.mkdir(parents=True)
    old_file = _write_pair(old_date)

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff, dry_run=True)

    assert result["files_planned"] == 2
    assert result["directories_planned"] == 1
    assert result["files_removed"] == 0
    assert result["bytes_freed"] == 0
    assert old_file.exists()
    assert old_date.exists()


@pytest.mark.asyncio
@_APPLY_POSIX
async def test_cleanup_old_files_preserves_recent_data(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)
    recent_date = tmp_path / "chembl" / "activity" / "2024-12-01"
    recent_date.mkdir(parents=True)
    recent_file = (
        recent_date / "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
    )
    recent_file.write_bytes(b"test data")

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff)

    assert result["files_removed"] == 0
    assert result["directories_removed"] == 0
    assert recent_file.exists()


@pytest.mark.asyncio
@_APPLY_POSIX
async def test_cleanup_old_files_multiple_providers(tmp_path: Path) -> None:
    writer = _make_writer(tmp_path)

    for provider in ["chembl", "pubchem"]:
        for entity in ["activity", "compound"]:
            old_date = tmp_path / provider / entity / "2024-01-01"
            old_date.mkdir(parents=True)
            _write_pair(old_date, b"data")

    cutoff = datetime(2024, 6, 1, tzinfo=UTC)
    result = await writer.cleanup_old_files(cutoff)

    assert result["files_removed"] == 8
    assert result["directories_removed"] == 4
