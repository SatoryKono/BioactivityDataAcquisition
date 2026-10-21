"""Cross-process coverage for the quarantine append lock."""

from __future__ import annotations

import multiprocessing
import sys
import time
from pathlib import Path

import pytest

from bioetl.infrastructure.quarantine.write_lock import (
    quarantine_append_lock,
    quarantine_write_lock_path,
)


def _hold_append_lock(base_path: str, ready: str, release: str) -> None:
    """Hold the append lock until the parent creates ``release``."""
    with quarantine_append_lock(base_path):
        Path(ready).write_text("ready", encoding="utf-8")
        deadline = time.monotonic() + 5
        while not Path(release).exists():
            if time.monotonic() > deadline:
                return
            time.sleep(0.01)


def _enter_append_lock(base_path: str, entered: str) -> None:
    """Record entry once the append lock is acquired."""
    with quarantine_append_lock(base_path):
        Path(entered).write_text("entered", encoding="utf-8")


@pytest.mark.unit
def test_write_lock_path_is_a_sibling_of_the_table(tmp_path: Path) -> None:
    """The lock file stays outside the Delta directory."""
    base = tmp_path / "quarantine"
    lock_path = quarantine_write_lock_path(str(base))
    assert lock_path == tmp_path / "quarantine.write.lock"


@pytest.mark.unit
def test_append_lock_blocks_another_process(tmp_path: Path) -> None:
    """A second process cannot pass the lock while the first still holds it."""
    try:
        context = multiprocessing.get_context("fork")
    except ValueError:
        pytest.skip("fork start method is unavailable")

    base = str(tmp_path / "quarantine")
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    entered = tmp_path / "entered"
    holder = context.Process(
        target=_hold_append_lock,
        args=(base, str(ready), str(release)),
    )
    waiter: multiprocessing.Process | None = None
    try:
        holder.start()
        deadline = time.monotonic() + 5
        while not ready.exists():
            assert time.monotonic() < deadline
            assert holder.exitcode is None
            time.sleep(0.01)
        waiter = context.Process(
            target=_enter_append_lock,
            args=(base, str(entered)),
        )
        waiter.start()
        blocked_until = time.monotonic() + 0.2
        while time.monotonic() < blocked_until:
            assert not entered.exists()
            time.sleep(0.01)
        release.write_text("release", encoding="utf-8")
        waiter.join(timeout=5)
        holder.join(timeout=5)
        assert entered.is_file()
        assert holder.exitcode == 0
        assert waiter.exitcode == 0
    finally:
        release.write_text("release", encoding="utf-8")
        for process in (waiter, holder):
            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout=2)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="posix flock probe")
def test_sibling_lock_file_is_exclusive_while_held(tmp_path: Path) -> None:
    """The sibling file is an exclusive flock while the append lock is held."""
    import fcntl

    base = str(tmp_path / "quarantine")
    with quarantine_append_lock(base):
        lock_path = quarantine_write_lock_path(base)
        with open(lock_path, "rb") as probe:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
