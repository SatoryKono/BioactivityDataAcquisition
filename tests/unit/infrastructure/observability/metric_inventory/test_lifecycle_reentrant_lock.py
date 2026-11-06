from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from bioetl.infrastructure.observability import metric_inventory

pytestmark = pytest.mark.unit


def test_reentrant_lock_normal_acquisition_and_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The collection lock is held during the call and released afterwards."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()
    lock_acquired = False
    run_count = 0

    def mock_collect_impl(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal lock_acquired, run_count
        run_count += 1
        lock_acquired = metric_inventory._COLLECTION_LOCK._is_owned()
        return {}

    monkeypatch.setattr(
        metric_inventory, "_collect_metric_inventory_impl", mock_collect_impl
    )
    metric_inventory.collect_metric_inventory(tmp_path)

    assert lock_acquired is True
    assert run_count == 1
    assert not metric_inventory._COLLECTION_LOCK._is_owned()


def test_reentrant_lock_error_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exception inside collection still releases the collection lock."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()

    def mock_collect_impl_error(*args: object, **kwargs: object) -> dict[str, object]:
        assert metric_inventory._COLLECTION_LOCK._is_owned()
        raise ValueError("Simulated error inside lock")

    monkeypatch.setattr(
        metric_inventory,
        "_collect_metric_inventory_impl",
        mock_collect_impl_error,
    )
    with pytest.raises(ValueError, match="Simulated error inside lock"):
        metric_inventory.collect_metric_inventory(tmp_path)

    assert not metric_inventory._COLLECTION_LOCK._is_owned()


def test_reentrant_lock_cancellation_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cancellation still releases the collection lock."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()

    def mock_collect_impl_cancellation(*args: object, **kwargs: object) -> dict[str, object]:
        assert metric_inventory._COLLECTION_LOCK._is_owned()
        raise asyncio.CancelledError()

    monkeypatch.setattr(
        metric_inventory,
        "_collect_metric_inventory_impl",
        mock_collect_impl_cancellation,
    )
    with pytest.raises(asyncio.CancelledError):
        metric_inventory.collect_metric_inventory(tmp_path)

    assert not metric_inventory._COLLECTION_LOCK._is_owned()


def test_reentrant_lock_timeout_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A timeout inside collection still releases the collection lock."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()

    def mock_collect_impl_timeout(*args: object, **kwargs: object) -> dict[str, object]:
        assert metric_inventory._COLLECTION_LOCK._is_owned()
        raise TimeoutError("Simulated timeout inside lock")

    monkeypatch.setattr(
        metric_inventory,
        "_collect_metric_inventory_impl",
        mock_collect_impl_timeout,
    )
    with pytest.raises(TimeoutError, match="Simulated timeout inside lock"):
        metric_inventory.collect_metric_inventory(tmp_path)

    assert not metric_inventory._COLLECTION_LOCK._is_owned()


def test_reentrant_lock_retry_acquires_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retry logic reacquires the lock correctly across calls."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()

    attempts = 0
    lock_history: list[bool] = []

    def mock_collect_impl_retry(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        lock_history.append(metric_inventory._COLLECTION_LOCK._is_owned())
        if attempts < 3:
            raise ValueError("Simulated error on retry")
        return {}

    monkeypatch.setattr(
        metric_inventory,
        "_collect_metric_inventory_impl",
        mock_collect_impl_retry,
    )

    for _ in range(2):
        with pytest.raises(ValueError):
            metric_inventory.collect_metric_inventory(tmp_path)
        assert not metric_inventory._COLLECTION_LOCK._is_owned()

    metric_inventory.collect_metric_inventory(tmp_path)
    assert attempts == 3
    assert lock_history == [True, True, True]
    assert not metric_inventory._COLLECTION_LOCK._is_owned()


@pytest.mark.xfail(reason="Negative control test intended to demonstrate failure when shutdown is missing", strict=True)
def test_reentrant_lock_missing_shutdown_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing shutdown (leak) in the lock mechanism fails tests."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()

    def mock_collect_impl_leak(*args: object, **kwargs: object) -> dict[str, object]:
        assert metric_inventory._COLLECTION_LOCK._is_owned()
        return {}

    # Simulate a corrupted lock release logic by bypassing the context manager entirely.
    def bad_collect(repo_root: Any) -> Any:
        metric_inventory._COLLECTION_LOCK.acquire()
        return mock_collect_impl_leak()

    monkeypatch.setattr(metric_inventory, "collect_metric_inventory", bad_collect)

    bad_collect(tmp_path)
    try:
        assert not metric_inventory._COLLECTION_LOCK._is_owned(), "Resource leak detected: reentrant lock was not released."
    finally:
        metric_inventory._COLLECTION_LOCK.release()
