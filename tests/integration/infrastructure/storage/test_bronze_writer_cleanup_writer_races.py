"""Pinned Bronze writer root race tests for FS-001."""

from __future__ import annotations

import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage import bronze_writer as bronze_writer_module
from bioetl.infrastructure.storage.bronze import cleanup_posix, read_cleanup_mixin
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    bronze_tree_lock,
    destructive_cleanup_supported,
)
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration
_APPLY_POSIX = pytest.mark.skipif(
    not destructive_cleanup_supported(),
    reason="POSIX anchored destructive capability required (Windows NOT_VERIFIED)",
)
CUTOFF = datetime(2024, 6, 1, tzinfo=UTC)


@_APPLY_POSIX
def test_waiting_cleaners_leave_writer_io_executor_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two exclusive waiters cannot consume the writer's two I/O workers."""
    root = tmp_path / "bronze"
    root.mkdir()
    writer = BronzeWriter(base_path=root, logger=NoOpLogger(), metrics=NoOpMetrics())
    original_lock = bronze_tree_lock
    waiter_count = 0
    waiter_guard = threading.Lock()

    async def interleave() -> None:
        nonlocal waiter_count
        loop = asyncio.get_running_loop()
        both_waiting = asyncio.Event()
        completed_io = threading.Event()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=2))

        @contextmanager
        def count_exclusive_waiters(base_path: Path, *, exclusive: bool):
            nonlocal waiter_count
            if exclusive:
                with waiter_guard:
                    waiter_count += 1
                    if waiter_count == 2:
                        loop.call_soon_threadsafe(both_waiting.set)
            with original_lock(base_path, exclusive=exclusive) as lease:
                yield lease

        monkeypatch.setattr(
            read_cleanup_mixin, "bronze_tree_lock", count_exclusive_waiters
        )
        cleaners: list[asyncio.Task[dict[str, int]]] = []
        try:
            with original_lock(root, exclusive=False):
                cleaners = [
                    asyncio.create_task(writer.cleanup_old_files(CUTOFF))
                    for _ in range(2)
                ]
                await asyncio.wait_for(both_waiting.wait(), timeout=5)
                await asyncio.wait_for(asyncio.to_thread(completed_io.set), timeout=5)
                assert completed_io.is_set()
        finally:
            await asyncio.gather(*cleaners)

    asyncio.run(interleave())
    assert waiter_count == 2


@_APPLY_POSIX
async def test_failed_completion_marker_retains_date_for_stage_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An uncommitted stage journal must retain its parent after unlink."""
    root = tmp_path / "bronze"
    date_dir = root / "chembl" / "activity" / "2024-01-01"
    date_dir.mkdir(parents=True)
    artifact = "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
    (date_dir / artifact).write_bytes(b"owned")
    (date_dir / f"{artifact}.meta.json").write_bytes(b"{}")
    writer = BronzeWriter(base_path=root, logger=NoOpLogger(), metrics=NoOpMetrics())
    original_rename = cleanup_posix.os.rename
    failed = False

    def fail_completion_marker(src: object, dst: object, **kwargs: object) -> None:
        nonlocal failed
        if (
            src == "origin.json"
            and str(dst).startswith(".bronze-cleanup-done-")
            and not failed
        ):
            failed = True
            raise PermissionError("completion marker denied")
        original_rename(src, dst, **kwargs)

    monkeypatch.setattr(cleanup_posix.os, "rename", fail_completion_marker)
    first = await writer.cleanup_old_files(CUTOFF)

    assert failed
    assert first["files_removed"] == 2
    assert first["bytes_freed"] == 7
    assert first["directories_failed"] == 1
    assert first["directories_skipped"] == 1
    assert first["directories_removed"] == 0
    assert date_dir.is_dir() and not list(date_dir.iterdir())
    assert list(root.glob(".bronze-cleanup-stage-*"))

    monkeypatch.setattr(cleanup_posix.os, "rename", original_rename)
    second = await writer.cleanup_old_files(CUTOFF)
    assert second["files_removed"] == 0
    assert second["directories_removed"] == 1
    assert not date_dir.exists()
    assert not list(root.glob(".bronze-cleanup-stage-*"))


@pytest.mark.skipif(
    not destructive_cleanup_supported(),
    reason="POSIX anchored lock capability required",
)
def test_non_regular_lock_refuses_without_blocking(tmp_path: Path) -> None:
    """A FIFO in place of the lock cannot stall or authorize cleanup."""
    root = tmp_path / "bronze"
    root.mkdir()
    os.mkfifo(root / ".bronze-cleanup.lock")
    sentinel = root / "sentinel"
    sentinel.write_bytes(b"retain")
    with pytest.raises(OSError, match="not a regular file"):
        with bronze_tree_lock(root, exclusive=True):
            pytest.fail("non-regular lock must not authorize cleanup")
    assert sentinel.read_bytes() == b"retain"


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
async def test_symlink_configured_writer_pins_target_but_cleanup_refuses_alias(
    tmp_path: Path,
) -> None:
    """An existing writer alias remains usable without authorizing apply through it."""
    target_root = tmp_path / "target"
    target_root.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target_root, target_is_directory=True)
    sentinel = target_root / "sentinel"
    sentinel.write_bytes(b"retain")
    writer = BronzeWriter(base_path=alias, logger=NoOpLogger(), metrics=NoOpMetrics())

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

    assert (target_root / result.relative_path).is_file()
    assert (target_root / f"{result.relative_path}.meta.json").is_file()
    with pytest.raises(OSError):
        await writer.cleanup_old_files(datetime(2025, 1, 1, tzinfo=UTC))
    assert sentinel.read_bytes() == b"retain"
    assert (target_root / result.relative_path).is_file()


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
