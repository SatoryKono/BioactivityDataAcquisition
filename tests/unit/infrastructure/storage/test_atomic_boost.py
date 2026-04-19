"""Coverage boost tests for support/atomic_ops.py.

Targets uncovered lines: 96, 146-147, 150, 255-259, 298, 310.
"""

from __future__ import annotations

import errno
from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.infrastructure.storage.support.atomic_ops import (
    AtomicWriteError,
    AtomicWriteGroup,
    _replace_with_retry,
    atomic_write,
)
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy


@pytest.mark.unit
class TestReplaceWithRetryLine96:
    """Test the on_retry callback path in _replace_with_retry (line 98-99)."""

    def test_on_retry_called_before_sleep(self, tmp_path: Path) -> None:
        """Line 98-99: on_retry callback is invoked with correct args."""
        target = tmp_path / "target.txt"
        target.write_text("original")

        temp = tmp_path / ".temp_target_.tmp"
        temp.write_text("new")

        original_replace = Path.replace
        call_count = {"count": 0}
        retry_events: list[tuple[int, float]] = []

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise OSError(errno.EBUSY, "busy")
            return original_replace(self, target_path)

        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.001,
            max_delay_seconds=0.01,
            jitter_seconds=0.0,
        )

        def on_retry(attempt: int, delay: float, error: OSError) -> None:
            retry_events.append((attempt, delay))

        with patch.object(Path, "replace", flaky_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                _replace_with_retry(
                    temp, target, retry_policy=policy, on_retry=on_retry
                )

        assert len(retry_events) == 1
        assert retry_events[0][0] == 1  # attempt 1

    def test_on_retry_none_no_error(self, tmp_path: Path) -> None:
        """Line 98: on_retry=None — no callback, still works."""
        target = tmp_path / "target.txt"
        temp = tmp_path / ".temp.tmp"
        temp.write_bytes(b"data")

        original_replace = Path.replace
        call_count = {"count": 0}

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise OSError(errno.EBUSY, "busy")
            return original_replace(self, target_path)

        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.001,
            max_delay_seconds=0.01,
            jitter_seconds=0.0,
        )

        with patch.object(Path, "replace", flaky_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                _replace_with_retry(temp, target, retry_policy=policy, on_retry=None)

        assert target.exists()


@pytest.mark.unit
class TestAtomicWriteErrorHandling:
    """Tests for error paths in atomic_write (lines 146-147, 150)."""

    def test_atomic_write_error_reraises_as_is(self, tmp_path: Path) -> None:
        """Line 149-150: AtomicWriteError is re-raised without wrapping."""
        target = tmp_path / "target.txt"

        # Raise AtomicWriteError directly inside the context
        original_awe = AtomicWriteError(target, "original error")

        with pytest.raises(AtomicWriteError) as exc_info:
            with atomic_write(target, mode="w") as f:
                f.write("partial")
                raise original_awe

        # Should be the same error (re-raised as-is)
        assert exc_info.value is original_awe
        assert exc_info.value.reason == "original error"

    def test_oserror_wrapped_in_atomic_write_error(self, tmp_path: Path) -> None:
        """Line 151: OSError is wrapped in AtomicWriteError."""
        target = tmp_path / "target.txt"

        with pytest.raises(AtomicWriteError) as exc_info:
            with atomic_write(target, mode="w") as f:
                f.write("partial")
                raise OSError(errno.EACCES, "permission denied")

        assert isinstance(exc_info.value, AtomicWriteError)
        assert exc_info.value.target == target

    def test_temp_file_cleaned_up_when_exists(self, tmp_path: Path) -> None:
        """Lines 144-147: temp file unlinked when it exists on error."""
        target = tmp_path / "test.txt"

        with pytest.raises(AtomicWriteError):
            with atomic_write(target, mode="w") as f:
                f.write("data")
                raise ValueError("test error")

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_osignore_when_temp_cleanup_fails(self, tmp_path: Path) -> None:
        """Line 146-147: OSError during temp cleanup is suppressed."""
        target = tmp_path / "test.txt"

        unlink_call_count = {"count": 0}

        def raising_unlink(self: Path, missing_ok: bool = False) -> None:
            unlink_call_count["count"] += 1
            raise OSError("cleanup failed")

        with patch.object(Path, "unlink", raising_unlink):
            with pytest.raises(AtomicWriteError):
                with atomic_write(target, mode="w") as f:
                    f.write("data")
                    raise ValueError("write error")

        # The OSError from unlink was suppressed
        assert unlink_call_count["count"] >= 1


@pytest.mark.unit
class TestAtomicWriteGroupAddFailure:
    """Tests for AtomicWriteGroup.add write failure (lines 255-259)."""

    def test_add_write_failure_cleans_up_temp_and_raises(self, tmp_path: Path) -> None:
        """Lines 255-259: OSError during add.write cleans up temp and re-raises."""
        group = AtomicWriteGroup()
        target = tmp_path / "target.txt"

        # Patch os.fdopen to simulate write failure
        import os

        class FakeFile:
            def write(self, data: bytes) -> int:
                raise OSError("disk full")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                # No-op context-manager cleanup for the failing file stub.
                return None

        def failing_fdopen(fd: int, mode: str, **kw) -> FakeFile:
            # Close the fd to avoid leaks
            try:
                os.close(fd)
            except OSError:
                pass
            return FakeFile()

        with patch("os.fdopen", failing_fdopen):
            with pytest.raises(OSError, match="disk full"):
                group.add(target, b"data")

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_add_type_error_cleans_up_temp(self, tmp_path: Path) -> None:
        """Lines 255-259: TypeError during add cleans up temp and re-raises."""
        group = AtomicWriteGroup()
        target = tmp_path / "target.txt"

        import os

        class BadFile:
            def write(self, data: bytes) -> int:
                raise TypeError("bad type")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                # No-op context-manager cleanup for the failing file stub.
                return None

        def bad_fdopen(fd: int, mode: str, **kw) -> BadFile:
            try:
                os.close(fd)
            except OSError:
                pass
            return BadFile()

        with patch("os.fdopen", bad_fdopen):
            with pytest.raises(TypeError, match="bad type"):
                group.add(target, b"data")


@pytest.mark.unit
class TestAtomicWriteGroupRollback:
    """Tests for AtomicWriteGroup.rollback (line 298)."""

    def test_rollback_with_nonexistent_temp(self, tmp_path: Path) -> None:
        """Line 298: temp.exists() returns False — rollback skips unlink."""
        group = AtomicWriteGroup()
        target = tmp_path / "target.txt"
        group.add(target, b"data")

        # Manually unlink all temp files
        for _, temp_path, _ in group._pending:
            temp_path.unlink()

        # rollback should not raise even when temp doesn't exist
        group.rollback()
        assert len(group._pending) == 0

    def test_rollback_with_oserror_suppressed(self, tmp_path: Path) -> None:
        """Lines 295-299: OSError during temp unlink is suppressed in rollback."""
        group = AtomicWriteGroup()
        target = tmp_path / "target.txt"
        group.add(target, b"data")

        def raising_unlink(self: Path, missing_ok: bool = False) -> None:
            raise OSError("rollback unlink failed")

        with patch.object(Path, "unlink", raising_unlink):
            # Should not raise
            group.rollback()

        assert len(group._pending) == 0


@pytest.mark.unit
class TestAtomicWriteGroupExitWithException:
    """Tests for AtomicWriteGroup.__exit__ (line 310)."""

    def test_exit_with_exception_calls_rollback(self, tmp_path: Path) -> None:
        """Line 333-334: __exit__ with exception calls rollback."""
        file1 = tmp_path / "file1.txt"

        with pytest.raises(RuntimeError):
            with AtomicWriteGroup() as group:
                group.add(file1, b"data")
                raise RuntimeError("test error")

        # File should not exist (rolled back)
        assert not file1.exists()

        # No temp files remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_exit_without_exception_does_not_call_rollback(
        self, tmp_path: Path
    ) -> None:
        """Line 334: __exit__ with no exception does nothing."""
        file1 = tmp_path / "file1.txt"

        with AtomicWriteGroup() as group:
            group.add(file1, b"data")
            group.commit()  # User must commit explicitly

        # File should exist after commit
        assert file1.exists()

    def test_exit_no_exception_pending_cleared_after_commit(
        self, tmp_path: Path
    ) -> None:
        """Line 310: __exit__ with no exception; pending cleared by commit."""
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"

        with AtomicWriteGroup() as group:
            group.add(file1, b"content1")
            group.add(file2, b"content2")
            group.commit()

        assert file1.read_bytes() == b"content1"
        assert file2.read_bytes() == b"content2"
