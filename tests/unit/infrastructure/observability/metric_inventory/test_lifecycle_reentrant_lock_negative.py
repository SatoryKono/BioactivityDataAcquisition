import pytest
from pathlib import Path
from bioetl.infrastructure.observability import metric_inventory

pytestmark = pytest.mark.unit


def test_missing_release_detectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A negative control test for a missed lock release
    assert not metric_inventory._COLLECTION_LOCK._is_owned()

    def mock_collect_impl(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("simulated early exit missing release")

    monkeypatch.setattr(
        metric_inventory, "_collect_metric_inventory_impl", mock_collect_impl
    )

    # Monkeypatch the standard collect function to simulate a developer forgetting to release
    original_collect = metric_inventory.collect_metric_inventory

    def leaky_collect(path: Path) -> dict[str, object]:
        metric_inventory._COLLECTION_LOCK.acquire()
        return mock_collect_impl(path)

    monkeypatch.setattr(metric_inventory, "collect_metric_inventory", leaky_collect)

    with pytest.raises(RuntimeError):
        metric_inventory.collect_metric_inventory(tmp_path)

    # The negative control confirms the harness catches the leak
    assert metric_inventory._COLLECTION_LOCK._is_owned()

    # cleanup for next tests
    metric_inventory._COLLECTION_LOCK.release()
