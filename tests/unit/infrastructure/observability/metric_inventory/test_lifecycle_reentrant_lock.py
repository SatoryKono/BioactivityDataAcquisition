from __future__ import annotations

import pytest

from bioetl.infrastructure.observability.metric_inventory import (
    _COLLECTION_LOCK,
    collect_metric_inventory,
)

pytestmark = pytest.mark.unit

def test_reentrant_lock_normal_acquisition_and_release(tmp_path) -> None:
    """Test normal acquisition and release of the _COLLECTION_LOCK."""
    assert not _COLLECTION_LOCK._is_owned()  # Initially unowned

    lock_acquired = False

    def mock_collect_impl(*args, **kwargs):
        nonlocal lock_acquired
        lock_acquired = _COLLECTION_LOCK._is_owned()
        return {}

    # We patch the inner implementation to avoid heavy I/O
    import bioetl.infrastructure.observability.metric_inventory as metric_inventory
    original_impl = metric_inventory._collect_metric_inventory_impl
    metric_inventory._collect_metric_inventory_impl = mock_collect_impl

    try:
        collect_metric_inventory(tmp_path)
    finally:
        metric_inventory._collect_metric_inventory_impl = original_impl

    assert lock_acquired is True
    assert not _COLLECTION_LOCK._is_owned()


def test_reentrant_lock_error_release(tmp_path) -> None:
    """Test release of the _COLLECTION_LOCK upon error."""
    assert not _COLLECTION_LOCK._is_owned()

    def mock_collect_impl_error(*args, **kwargs):
        assert _COLLECTION_LOCK._is_owned()
        raise ValueError("Simulated error inside lock")

    import bioetl.infrastructure.observability.metric_inventory as metric_inventory
    original_impl = metric_inventory._collect_metric_inventory_impl
    metric_inventory._collect_metric_inventory_impl = mock_collect_impl_error

    try:
        with pytest.raises(ValueError, match="Simulated error inside lock"):
            collect_metric_inventory(tmp_path)
    finally:
        metric_inventory._collect_metric_inventory_impl = original_impl

    assert not _COLLECTION_LOCK._is_owned()
