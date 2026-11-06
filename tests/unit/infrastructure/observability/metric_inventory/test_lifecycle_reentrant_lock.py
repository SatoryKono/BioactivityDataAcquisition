from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.observability import metric_inventory

pytestmark = pytest.mark.unit


def test_reentrant_lock_normal_acquisition_and_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The collection lock is held during the call and released afterwards."""
    assert not metric_inventory._COLLECTION_LOCK._is_owned()
    lock_acquired = False

    def mock_collect_impl(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal lock_acquired
        lock_acquired = metric_inventory._COLLECTION_LOCK._is_owned()
        return {}

    monkeypatch.setattr(
        metric_inventory, "_collect_metric_inventory_impl", mock_collect_impl
    )
    metric_inventory.collect_metric_inventory(tmp_path)

    assert lock_acquired is True
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
