from pathlib import Path
from threading import RLock

import pytest

from bioetl.infrastructure.observability import metric_inventory
from tests.unit.infrastructure.observability.metric_inventory.test_lifecycle_reentrant_lock import (
    test_reentrant_lock_normal_acquisition_and_release as _check_normal_lifecycle,
)

pytestmark = pytest.mark.unit


class _MissingReleaseLock:
    """Use an isolated RLock while simulating an omitted context-manager release."""

    def __init__(self) -> None:
        self.lock = RLock()

    def __enter__(self) -> None:
        self.lock.acquire()

    def __exit__(self, *exc: object) -> None:
        pass

    def _is_owned(self) -> bool:
        return self.lock._is_owned()


def test_missing_release_detectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = _MissingReleaseLock()
    with monkeypatch.context() as isolated:
        isolated.setattr(metric_inventory, "_COLLECTION_LOCK", lock)
        try:
            with pytest.raises(AssertionError, match="missing-release"):
                _check_normal_lifecycle(tmp_path, isolated)
        finally:
            if lock._is_owned():
                lock.lock.release()
