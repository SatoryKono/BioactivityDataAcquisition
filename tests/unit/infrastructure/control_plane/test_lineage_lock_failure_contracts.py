"""Windows locking retries only deadlock and preserves rollback failures."""

import errno
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.infrastructure.control_plane import file_lineage_store as lineage

pytestmark = pytest.mark.unit


def test_windows_deadlock_is_retried_but_access_denied_propagates(tmp_path):
    descriptor = os.open(tmp_path / "lock", os.O_CREAT | os.O_RDWR)
    try:
        lock = Mock(side_effect=[OSError(errno.EDEADLK, "retry"), None])
        lineage._acquire_msvcrt_lock(descriptor, locking=lock, lock_mode=1)
        assert lock.call_count == 2
        assert os.fstat(descriptor).st_size == 1
        denied = OSError(errno.EACCES, "permission denied")
        lock = Mock(side_effect=denied)
        with pytest.raises(OSError) as caught:
            lineage._acquire_msvcrt_lock(descriptor, locking=lock, lock_mode=1)
        assert caught.value is denied
        lock.assert_called_once_with(descriptor, 1, 1)
    finally:
        os.close(descriptor)


def test_windows_lock_and_unlock_select_the_crt_modes(tmp_path, monkeypatch):
    locking = Mock()
    monkeypatch.setitem(
        sys.modules, "msvcrt", SimpleNamespace(locking=locking, LK_LOCK=1, LK_UNLCK=0)
    )
    monkeypatch.setattr(lineage, "sys", SimpleNamespace(platform="win32"))
    descriptor = os.open(tmp_path / "lock", os.O_CREAT | os.O_RDWR)
    try:
        lineage._acquire_exclusive_lock(descriptor)
        lineage._release_exclusive_lock(descriptor)
        assert [item.args for item in locking.call_args_list] == [
            (descriptor, 1, 1),
            (descriptor, 0, 1),
        ]
    finally:
        os.close(descriptor)


def test_failed_fragment_delete_is_retained_as_rollback_error(tmp_path, monkeypatch):
    path = tmp_path / "fragment.json"
    path.write_text("new", encoding="utf-8")
    error = OSError("fragment locked")
    original_unlink = type(path).unlink

    def unlink(target, *args, **kwargs):
        if target == path:
            raise error
        return original_unlink(target, *args, **kwargs)

    monkeypatch.setattr(type(path), "unlink", unlink)
    store = lineage.FileLineageStore(tmp_path)
    errors = store._rollback_save(
        fragment_path=path, existing_fragment_payload=None, index_rollbacks=[]
    )
    assert errors == [error]
    assert path.read_text(encoding="utf-8") == "new"
