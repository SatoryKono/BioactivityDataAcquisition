"""Pinned Bronze writer root race tests for FS-001."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage import bronze_writer as bronze_writer_module
from bioetl.infrastructure.storage.bronze.cleanup_support import bronze_tree_lock
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration
_APPLY_POSIX = pytest.mark.skipif(
    os.name == "nt", reason="Windows destructive cleanup is fail-closed (NOT_VERIFIED)"
)
CUTOFF = datetime(2024, 6, 1, tzinfo=UTC)


@_APPLY_POSIX
async def test_writer_uses_pinned_root_after_alias_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Payload, sidecar and optional copy stay under the shared-locked root."""
    old_root, new_root = tmp_path / "old", tmp_path / "new"
    new_root.mkdir()
    alias = tmp_path / "alias"
    alias.mkdir()
    writer = BronzeWriter(
        base_path=alias,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    original_lock = bronze_tree_lock
    switched = False

    @contextmanager
    def switch_after_lock(base_path: Path, *, exclusive: bool):
        nonlocal switched
        with original_lock(base_path, exclusive=exclusive) as locked_root:
            alias.rename(old_root)
            alias.symlink_to(new_root, target_is_directory=True)
            switched = True
            yield locked_root

    monkeypatch.setattr(bronze_writer_module, "bronze_tree_lock", switch_after_lock)
    batch_id = BatchID(UUID(int=1))
    result = await writer.write_bronze(
        records=iter([b"{}\n"]),
        provider="chembl",
        entity="activity",
        date=CUTOFF,
        batch_id=batch_id,
        run_id=RunID(UUID(int=2)),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=CUTOFF,
    )
    assert switched
    expected = Path(result.relative_path)
    assert (old_root / expected).is_file()
    assert (old_root / f"{expected}.meta.json").is_file()
    assert (old_root / expected.with_suffix("")).is_file()
    assert Path(result.absolute_path) == old_root / expected
    assert not list(new_root.rglob("batch_*"))


@_APPLY_POSIX
async def test_writer_uses_locked_root_inode_after_root_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-name replacement cannot receive writes under the old root lock."""
    root = tmp_path / "bronze"
    root.mkdir()
    moved = tmp_path / "moved_bronze"
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    outside = replacement / "sentinel"
    outside.write_bytes(b"outside")
    writer = BronzeWriter(
        base_path=root,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    original_lock = bronze_tree_lock

    @contextmanager
    def replace_after_lock(base_path: Path, *, exclusive: bool):
        with original_lock(base_path, exclusive=exclusive) as locked_root:
            root.rename(moved)
            replacement.rename(root)
            yield locked_root

    monkeypatch.setattr(bronze_writer_module, "bronze_tree_lock", replace_after_lock)
    result = await writer.write_bronze(
        records=iter([b"{}\n"]),
        provider="chembl",
        entity="activity",
        date=CUTOFF,
        batch_id=BatchID(UUID(int=1)),
        run_id=RunID(UUID(int=2)),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=CUTOFF,
    )
    expected = Path(result.relative_path)
    assert (moved / expected).is_file()
    assert (moved / f"{expected}.meta.json").is_file()
    assert (moved / expected.with_suffix("")).is_file()
    assert Path(result.absolute_path) == moved / expected
    assert (root / "sentinel").read_bytes() == b"outside"
    assert not list(root.rglob("batch_*"))
