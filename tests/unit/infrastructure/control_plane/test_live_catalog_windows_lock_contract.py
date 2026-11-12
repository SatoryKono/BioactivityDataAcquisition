"""Windows catalog locking is tested without taking any shared backend lock."""

from __future__ import annotations

import errno
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from bioetl.infrastructure.control_plane import live_run_manifest_catalog as subject

pytestmark = pytest.mark.unit


def test_windows_acquire_and_release_use_distinct_crt_modes(monkeypatch):
    crt = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2)
    monkeypatch.setitem(sys.modules, "msvcrt", crt)
    monkeypatch.setattr(subject, "sys", SimpleNamespace(platform="win32"))
    acquire, release = Mock(), Mock()
    monkeypatch.setattr(subject, "_acquire_windows_lock", acquire)
    monkeypatch.setattr(subject, "_lock_byte", release)
    subject._acquire_exclusive_lock(123)
    subject._release_exclusive_lock(123)
    acquire.assert_called_once_with(123, 1)
    release.assert_called_once_with(123, 2)


def test_only_crt_deadlock_is_retried(monkeypatch):
    lock = Mock(side_effect=[OSError(errno.EDEADLK, "synthetic contention"), None])
    monkeypatch.setattr(subject, "_lock_byte", lock)
    subject._acquire_windows_lock(123, 1)
    assert lock.call_count == 2
    lock.reset_mock(side_effect=True)
    lock.side_effect = PermissionError(errno.EACCES, "synthetic refusal")
    with pytest.raises(PermissionError):
        subject._acquire_windows_lock(123, 1)
    lock.assert_called_once_with(123, 1)


def test_byte_lock_initializes_only_its_owned_fixture_file(monkeypatch, tmp_path):
    locking = Mock()
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=locking))
    monkeypatch.setattr(subject, "sys", SimpleNamespace(platform="win32"))
    path = tmp_path / "fixture.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        subject._lock_byte(descriptor, 1)
        locking.assert_called_once_with(descriptor, 1, 1)
        assert path.read_bytes() == b"\0"
    finally:
        os.close(descriptor)


def test_byte_lock_refuses_non_windows_platform(monkeypatch):
    monkeypatch.setattr(subject, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(RuntimeError, match="require Windows"):
        subject._lock_byte(123, 1)
