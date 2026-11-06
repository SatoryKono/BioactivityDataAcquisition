"""Regression coverage for the metric inventory collection lock."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path

import pytest

from bioetl.infrastructure.observability import metric_inventory

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("fail_read", [False, True], ids=["normal", "error"])
def test_collection_lock_released_after_inventory_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_read: bool
) -> None:
    """A competing thread can take the lock only after collection exits."""
    lock = metric_inventory._COLLECTION_LOCK
    load_definitions = metric_inventory._load_declared_metric_definitions

    def try_acquire() -> bool:
        acquired = lock.acquire(blocking=False)
        if acquired:
            lock.release()
        return acquired

    with ThreadPoolExecutor(max_workers=1) as contender:

        def observe_read(repo_root: Path) -> dict[str, set[str]]:
            assert not contender.submit(try_acquire).result(timeout=5)
            if fail_read:
                raise OSError("injected inventory read failure")
            return load_definitions(repo_root)

        monkeypatch.setattr(
            metric_inventory, "_load_declared_metric_definitions", observe_read
        )
        outcome = (
            pytest.raises(OSError, match="injected inventory read failure")
            if fail_read
            else nullcontext()
        )
        with outcome:
            metric_inventory.collect_metric_inventory(tmp_path)

        assert contender.submit(try_acquire).result(timeout=5)
