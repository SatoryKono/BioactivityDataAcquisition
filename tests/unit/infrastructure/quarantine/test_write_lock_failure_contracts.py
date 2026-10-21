"""Platform lock failures retain retry semantics and descriptor ownership."""

from __future__ import annotations

import errno
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from bioetl.infrastructure.quarantine import write_lock as locks


def test_append_lock_owns_and_reuses_the_thread_lock(tmp_path):
    base = str(tmp_path / "table")
    with locks.quarantine_append_lock(base):
        held = locks._thread_lock(base)
        assert held.locked()
        assert locks.quarantine_write_lock_path(base).is_file()
    assert not held.locked()
    assert locks._thread_lock(base) is held


def test_windows_acquire_and_release_select_the_correct_byte_lock(monkeypatch):
    crt = SimpleNamespace(locking=Mock(), LK_LOCK=1, LK_UNLCK=2)
    monkeypatch.setitem(sys.modules, "msvcrt", crt)
    monkeypatch.setattr(locks, "sys", SimpleNamespace(platform="win32"))
    acquire, release = Mock(), Mock()
    monkeypatch.setattr(locks, "_acquire_windows_lock", acquire)
    monkeypatch.setattr(locks, "_lock_byte", release)
    locks._acquire_exclusive_lock(11)
    locks._release_exclusive_lock(11)
    acquire.assert_called_once_with(11, crt.locking, 1)
    release.assert_called_once_with(11, crt.locking, 2)


def test_posix_acquire_and_release_select_exclusive_then_unlock(monkeypatch):
    posix = SimpleNamespace(flock=Mock(), LOCK_EX=2, LOCK_UN=8)
    monkeypatch.setattr(locks, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(locks, "fcntl", posix, raising=False)
    locks._acquire_exclusive_lock(11)
    locks._release_exclusive_lock(11)
    assert posix.flock.call_args_list == [call(11, 2), call(11, 8)]


def test_windows_deadlock_is_retried_until_the_byte_lock_is_held(monkeypatch):
    lock_byte = Mock(side_effect=[OSError(errno.EDEADLK, "busy"), None])
    monkeypatch.setattr(locks, "_lock_byte", lock_byte)
    locking = Mock()
    locks._acquire_windows_lock(11, locking, 1)
    assert lock_byte.call_args_list == [call(11, locking, 1), call(11, locking, 1)]


def test_windows_permission_error_propagates_without_retry(monkeypatch):
    error = OSError(errno.EACCES, "denied")
    lock_byte = Mock(side_effect=error)
    monkeypatch.setattr(locks, "_lock_byte", lock_byte)
    with pytest.raises(OSError) as caught:
        locks._acquire_windows_lock(11, Mock(), 1)
    assert caught.value is error
    assert lock_byte.call_count == 1


def test_byte_lock_initializes_an_empty_file_once(tmp_path):
    fd = os.open(tmp_path / "lock", os.O_CREAT | os.O_RDWR)
    locking = Mock()
    try:
        locks._lock_byte(fd, locking, 1)
        locks._lock_byte(fd, locking, 2)
        assert os.fstat(fd).st_size == 1
        assert os.lseek(fd, 0, os.SEEK_CUR) == 0
        assert locking.call_args_list == [call(fd, 1, 1), call(fd, 2, 1)]
    finally:
        os.close(fd)


@pytest.mark.parametrize("phase", ["acquire", "body", "release"])
def test_file_lock_closes_its_descriptor_after_each_failure(
    monkeypatch, tmp_path, phase
):
    seen = []

    def acquire(fd):
        seen.append(fd)
        if phase == "acquire":
            raise PermissionError("acquire denied")

    release = Mock(side_effect=OSError("unlock failed") if phase == "release" else None)
    monkeypatch.setattr(locks, "_acquire_exclusive_lock", acquire)
    monkeypatch.setattr(locks, "_release_exclusive_lock", release)
    if phase == "release":
        with locks._file_lock(tmp_path / "lock"):
            assert os.fstat(seen[0]).st_size == 0
    else:
        with pytest.raises((PermissionError, RuntimeError)):
            with locks._file_lock(tmp_path / "lock"):
                raise RuntimeError("body failed")
    assert release.call_count == (0 if phase == "acquire" else 1)
    with pytest.raises(OSError) as closed:
        os.fstat(seen[0])
    assert closed.value.errno == errno.EBADF
