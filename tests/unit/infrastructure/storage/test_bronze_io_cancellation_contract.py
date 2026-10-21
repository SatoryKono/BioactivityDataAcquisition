"""Cancellation must wait for owned Bronze I/O before releasing its tree lock."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from bioetl.infrastructure.storage import bronze_writer
from bioetl.infrastructure.storage.bronze import read_cleanup_mixin as cleanup

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_cancelled_bronze_writer_drains_write_before_releasing_lock(
    tmp_path, monkeypatch
):
    started, released = asyncio.Event(), asyncio.Event()
    lock = MagicMock()
    lock.__enter__.return_value = SimpleNamespace(writer_path=tmp_path)
    monkeypatch.setattr(
        bronze_writer, "_prepare_unlinked_bronze_root", lambda path: None
    )
    monkeypatch.setattr(bronze_writer, "bronze_tree_lock", lambda *args, **kwargs: lock)

    async def write(request, path):
        started.set()
        await released.wait()
        return object()

    host = SimpleNamespace(base_path=tmp_path, _write_bronze_with_tracing=write)
    task = asyncio.create_task(
        bronze_writer.BronzeWriter._write_bronze_under_lock(host, object())
    )
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    lock.__exit__.assert_not_called()
    released.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    lock.__exit__.assert_called_once_with(None, None, None)


def test_cleanup_stage_error_callback_counts_failure_without_claiming_success(
    tmp_path, monkeypatch
):
    writer = cleanup.BronzeWriterReadCleanupMixin()
    writer.base_path = tmp_path
    writer._log_cleanup_skip = Mock()
    stats = {
        "files_failed": 0,
        "files_conflicted": 0,
        "directories_failed": 0,
        "directories_conflicted": 0,
        "directories_removed": 0,
        "directories_skipped": 0,
    }
    plan = SimpleNamespace(path=tmp_path / "old", identity=object(), removable=True)

    def failed_stage(*args, on_stage_error, **kwargs):
        on_stage_error("stage", OSError("stage locked"))
        return False

    monkeypatch.setattr(cleanup, "safe_rmdir", failed_stage)
    writer._apply_cleanup_plan(
        stats, plan, tmp_path, tmp_path, None, SimpleNamespace(apply=Mock())
    )
    assert stats["directories_failed"] == 1 and stats["directories_removed"] == 0
    writer._log_cleanup_skip.assert_any_call(
        str(tmp_path / "stage"), "stage_cleanup_error"
    )
