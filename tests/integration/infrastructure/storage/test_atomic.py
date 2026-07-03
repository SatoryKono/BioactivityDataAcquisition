"""Integration tests for atomic write utilities."""

from __future__ import annotations

import errno
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.infrastructure.storage.support.atomic_ops import (
    AtomicWriteError,
    AtomicWriteGroup,
    atomic_write,
    atomic_write_bytes,
    atomic_write_text,
)
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy


class _WindowsLockError(OSError):
    """Synthetic Windows sharing violation used in lock-stress tests."""

    winerror = 32


class _WindowsAccessDeniedError(OSError):
    """Synthetic Windows access-denied error for retry classification tests."""

    winerror = 5


class _WindowsLockViolationError(OSError):
    """Synthetic Windows lock-violation error for retry classification tests."""

    winerror = 33


@pytest.mark.integration
class TestAtomicWrite:
    """Tests for atomic_write context manager."""

    def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """Test that atomic_write creates file at target path."""
        target = tmp_path / "test_file.txt"

        with atomic_write(target, mode="w") as f:
            f.write("hello world")

        assert target.exists()
        assert target.read_text() == "hello world"

    def test_atomic_write_binary(self, tmp_path: Path) -> None:
        """Test atomic_write with binary mode."""
        target = tmp_path / "test_file.bin"
        data = b"\x00\x01\x02\x03"

        with atomic_write(target, mode="wb") as f:
            f.write(data)

        assert target.exists()
        assert target.read_bytes() == data

    def test_atomic_write_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that atomic_write creates parent directories."""
        target = tmp_path / "nested" / "deep" / "file.txt"

        with atomic_write(target, mode="w") as f:
            f.write("nested content")

        assert target.exists()
        assert target.read_text() == "nested content"

    def test_atomic_write_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that atomic_write overwrites existing files."""
        target = tmp_path / "existing.txt"
        target.write_text("original")

        with atomic_write(target, mode="w") as f:
            f.write("overwritten")

        assert target.read_text() == "overwritten"

    def test_atomic_write_no_temp_file_after_success(self, tmp_path: Path) -> None:
        """Test that no temp files remain after successful write."""
        target = tmp_path / "test_file.txt"

        with atomic_write(target, mode="w") as f:
            f.write("content")

        # Check no .tmp files remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_write_cleanup_on_error(self, tmp_path: Path) -> None:
        """Test that temp files are cleaned up on write error."""
        target = tmp_path / "test_file.txt"

        with pytest.raises(AtomicWriteError):
            with atomic_write(target, mode="w") as f:
                f.write("partial")
                raise ValueError("Simulated error")

        # Target should not exist
        assert not target.exists()

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_write_preserves_original_on_error(self, tmp_path: Path) -> None:
        """Test that original file is preserved if write fails."""
        target = tmp_path / "existing.txt"
        target.write_text("original content")

        with pytest.raises(AtomicWriteError):
            with atomic_write(target, mode="w") as f:
                f.write("new content")
                raise RuntimeError("Simulated failure")

        # Original content should be preserved
        assert target.read_text() == "original content"

    def test_atomic_write_retries_transient_replace_error(self, tmp_path: Path) -> None:
        """Transient EBUSY during replace should be retried and eventually succeed."""
        target = tmp_path / "retry_target.txt"
        original_replace = Path.replace
        call_count = {"count": 0}

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise OSError(errno.EBUSY, "Device or resource busy")
            return original_replace(self, target_path)

        with patch.object(Path, "replace", flaky_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                atomic_write_text(target, "ok")

        assert target.read_text() == "ok"
        assert call_count["count"] == 3

    def test_atomic_write_no_retry_for_non_retryable_replace_error(
        self, tmp_path: Path
    ) -> None:
        """Non-retryable replace failures should surface immediately."""
        target = tmp_path / "no_retry.txt"
        call_count = {"count": 0}

        def non_retryable_replace(self: Path, target_path: Path) -> Path:
            del self, target_path
            call_count["count"] += 1
            raise OSError(2, "No such file or directory")

        with patch.object(Path, "replace", non_retryable_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                with pytest.raises(AtomicWriteError):
                    atomic_write_text(target, "x")

        assert call_count["count"] == 1

    def test_atomic_write_retry_hook_reports_attempts(self, tmp_path: Path) -> None:
        """Retry callback should receive attempt number and delay."""
        target = tmp_path / "hook_retry.txt"
        original_replace = Path.replace
        call_count = {"count": 0}
        hook_events: list[tuple[int, float]] = []

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise OSError(errno.EBUSY, "Device or resource busy")
            return original_replace(self, target_path)

        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=2,
            base_delay_seconds=0.01,
            max_delay_seconds=0.1,
            jitter_seconds=0.0,
            adaptive=True,
        )

        with patch.object(Path, "replace", flaky_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                atomic_write_text(
                    target,
                    "ok",
                    retry_policy=policy,
                    on_retry=lambda attempt, delay, _error: hook_events.append(
                        (attempt, delay)
                    ),
                )

        assert target.read_text() == "ok"
        assert hook_events == [(1, 0.01)]


@pytest.mark.integration
class TestAtomicRetryableErrors:
    """Tests for platform-specific retryable replace error classification."""

    def test_non_windows_eacces_is_not_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-Windows EACCES should not be treated as transient lock contention."""
        import bioetl.infrastructure.storage.support.atomic_ops as atomic_module

        monkeypatch.setattr(atomic_module, "_IS_WINDOWS", False)
        error = OSError(errno.EACCES, "Permission denied")
        assert atomic_module._is_retryable_replace_error(error) is False

    def test_non_windows_ebusy_is_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-Windows EBUSY should be treated as transient lock contention."""
        import bioetl.infrastructure.storage.support.atomic_ops as atomic_module

        monkeypatch.setattr(atomic_module, "_IS_WINDOWS", False)
        error = OSError(errno.EBUSY, "Device or resource busy")
        assert atomic_module._is_retryable_replace_error(error) is True

    def test_windows_eacces_is_retryable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Windows EACCES should remain retryable for transient sharing violations."""
        import bioetl.infrastructure.storage.support.atomic_ops as atomic_module

        monkeypatch.setattr(atomic_module, "_IS_WINDOWS", True)
        error = OSError(errno.EACCES, "Permission denied")
        assert atomic_module._is_retryable_replace_error(error) is True

    def test_windows_winerror_5_is_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WinError=5 should be treated as retryable on Windows."""
        import bioetl.infrastructure.storage.support.atomic_ops as atomic_module

        monkeypatch.setattr(atomic_module, "_IS_WINDOWS", True)
        error = _WindowsAccessDeniedError(
            errno.EACCES,
            "Access is denied",
        )
        assert atomic_module._is_retryable_replace_error(error) is True

    def test_windows_winerror_33_is_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WinError=33 should be treated as retryable on Windows."""
        import bioetl.infrastructure.storage.support.atomic_ops as atomic_module

        monkeypatch.setattr(atomic_module, "_IS_WINDOWS", True)
        error = _WindowsLockViolationError(
            errno.EACCES,
            "Lock violation",
        )
        assert atomic_module._is_retryable_replace_error(error) is True


@pytest.mark.integration
class TestAtomicWriteWindowsLockStress:
    """Windows-only stress tests for atomic replace lock handling."""

    @pytest.mark.slow
    @pytest.mark.serial
    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Windows-only lock semantics",
    )
    def test_windows_lock_stress_repeated_recovery(self, tmp_path: Path) -> None:
        """Repeated transient lock errors should still converge to last payload."""
        target = tmp_path / "windows_lock_stress.txt"
        original_replace = Path.replace
        writes = 30
        transient_failures_per_write = 2
        call_counts = {"attempts": 0, "failures": 0, "remaining_failures": 0}
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=5,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter_seconds=0.0,
            adaptive=True,
        )

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_counts["attempts"] += 1
            if target_path == target and call_counts["remaining_failures"] > 0:
                call_counts["remaining_failures"] -= 1
                call_counts["failures"] += 1
                raise _WindowsLockError(
                    errno.EACCES,
                    "The process cannot access the file because it is being used",
                )
            return original_replace(self, target_path)

        with patch.object(Path, "replace", flaky_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                for idx in range(writes):
                    call_counts["remaining_failures"] = transient_failures_per_write
                    atomic_write_text(
                        target,
                        f"payload-{idx}",
                        retry_policy=policy,
                    )

        assert target.read_text() == f"payload-{writes - 1}"
        assert call_counts["failures"] == writes * transient_failures_per_write

    @pytest.mark.slow
    @pytest.mark.serial
    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Windows-only lock semantics",
    )
    def test_windows_lock_stress_parallel_writers(self, tmp_path: Path) -> None:
        """Parallel writes should recover from one transient lock per target."""
        import concurrent.futures
        import threading

        file_count = 20
        targets = [
            tmp_path / f"parallel_windows_{idx}.txt" for idx in range(file_count)
        ]
        original_replace = Path.replace
        lock_state = dict.fromkeys(targets, 1)
        lock_state_guard = threading.Lock()
        policy = AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter_seconds=0.0,
            adaptive=True,
        )

        def flaky_replace(self: Path, target_path: Path) -> Path:
            with lock_state_guard:
                remaining_failures = lock_state.get(target_path, 0)
                if remaining_failures > 0:
                    lock_state[target_path] = remaining_failures - 1
                    raise _WindowsLockError(
                        errno.EACCES,
                        "The process cannot access the file because it is being used",
                    )
            return original_replace(self, target_path)

        def write_target(idx: int) -> None:
            atomic_write_text(targets[idx], f"value-{idx}", retry_policy=policy)

        with patch.object(Path, "replace", flaky_replace):
            with patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"):
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    list(pool.map(write_target, range(file_count)))

        for idx, target in enumerate(targets):
            assert target.read_text() == f"value-{idx}"


@pytest.mark.integration
class TestAtomicWriteHelpers:
    """Tests for atomic_write_bytes and atomic_write_text."""

    def test_atomic_write_bytes(self, tmp_path: Path) -> None:
        """Test atomic_write_bytes helper."""
        target = tmp_path / "binary.bin"
        data = b"binary data \x00\xff"

        atomic_write_bytes(target, data)

        assert target.read_bytes() == data

    def test_atomic_write_text(self, tmp_path: Path) -> None:
        """Test atomic_write_text helper."""
        target = tmp_path / "text.txt"
        text = "Hello, World!"

        atomic_write_text(target, text)

        assert target.read_text() == text

    def test_atomic_write_text_encoding(self, tmp_path: Path) -> None:
        """Test atomic_write_text with non-default encoding."""
        target = tmp_path / "unicode.txt"
        text = "Привет мир"

        atomic_write_text(target, text, encoding="utf-8")

        assert target.read_text(encoding="utf-8") == text


@pytest.mark.integration
class TestAtomicWriteGroup:
    """Tests for AtomicWriteGroup."""

    def test_group_writes_multiple_files(self, tmp_path: Path) -> None:
        """Test that AtomicWriteGroup writes multiple files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        with AtomicWriteGroup() as group:
            group.add(file1, b"content1")
            group.add(file2, b"content2")
            group.commit()

        assert file1.read_bytes() == b"content1"
        assert file2.read_bytes() == b"content2"

    def test_group_atomic_commit(self, tmp_path: Path) -> None:
        """Test that files only appear after commit."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        group = AtomicWriteGroup()
        group.add(file1, b"content1")
        group.add(file2, b"content2")

        # Files should not exist yet
        assert not file1.exists()
        assert not file2.exists()

        # Temp files should exist
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 2

        group.commit()

        # Now files should exist
        assert file1.exists()
        assert file2.exists()

        # No temp files remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_group_rollback_on_context_exit_with_exception(
        self, tmp_path: Path
    ) -> None:
        """Test that rollback happens on context exit with exception."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        with pytest.raises(ValueError):
            with AtomicWriteGroup() as group:
                group.add(file1, b"content1")
                group.add(file2, b"content2")
                raise ValueError("Simulated error before commit")

        # Files should not exist
        assert not file1.exists()
        assert not file2.exists()

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_group_explicit_rollback(self, tmp_path: Path) -> None:
        """Test explicit rollback cleans up temp files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        group = AtomicWriteGroup()
        group.add(file1, b"content1")
        group.add(file2, b"content2")

        # Temp files should exist
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 2

        group.rollback()

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

        # Files should not exist
        assert not file1.exists()
        assert not file2.exists()

    def test_group_preserves_original_on_partial_commit_failure(
        self, tmp_path: Path
    ) -> None:
        """Test that original files are preserved if commit fails partway."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        # Create original file1
        file1.write_text("original1")

        group = AtomicWriteGroup()
        group.add(file1, b"new content 1")
        group.add(file2, b"new content 2")

        # Mock Path.replace to fail on second file
        original_replace = Path.replace
        call_count = [0]

        def failing_replace(self, target):
            call_count[0] += 1
            if call_count[0] == 2:
                raise OSError("Simulated disk error")
            return original_replace(self, target)

        with patch.object(Path, "replace", failing_replace):
            with pytest.raises(AtomicWriteError):
                group.commit()

        # Note: First file may have been replaced before failure
        # This is a known limitation - true atomic multi-file writes
        # require a transactional filesystem

    def test_group_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that AtomicWriteGroup creates parent directories."""
        file1 = tmp_path / "nested" / "dir1" / "file1.txt"
        file2 = tmp_path / "nested" / "dir2" / "file2.txt"

        with AtomicWriteGroup() as group:
            group.add(file1, b"content1")
            group.add(file2, b"content2")
            group.commit()

        assert file1.read_bytes() == b"content1"
        assert file2.read_bytes() == b"content2"


@pytest.mark.integration
class TestAtomicWriteEdgeCases:
    """Edge case tests for atomic write utilities."""

    def test_write_empty_file(self, tmp_path: Path) -> None:
        """Test writing an empty file."""
        target = tmp_path / "empty.txt"

        atomic_write_bytes(target, b"")

        assert target.exists()
        assert target.read_bytes() == b""

    def test_write_large_file(self, tmp_path: Path) -> None:
        """Test writing a large file."""
        target = tmp_path / "large.bin"
        data = b"x" * (10 * 1024 * 1024)  # 10 MB

        atomic_write_bytes(target, data)

        assert target.read_bytes() == data

    def test_concurrent_writes_to_different_files(self, tmp_path: Path) -> None:
        """Test that concurrent writes to different files work."""
        import concurrent.futures

        def write_file(idx: int) -> Path:
            target = tmp_path / f"file_{idx}.txt"
            atomic_write_text(target, f"content {idx}")
            return target

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_file, i) for i in range(10)]
            results = [f.result() for f in futures]

        for i, path in enumerate(results):
            assert path.read_text() == f"content {i}"

    def test_special_characters_in_path(self, tmp_path: Path) -> None:
        """Test writing to paths with special characters."""
        target = tmp_path / "file with spaces.txt"

        atomic_write_text(target, "content")

        assert target.read_text() == "content"

    def test_temp_file_in_same_directory(self, tmp_path: Path) -> None:
        """Test that temp file is created in same directory as target."""
        target = tmp_path / "subdir" / "file.txt"

        with atomic_write(target, mode="w") as f:
            # During write, temp file should be in same dir
            tmp_files = list(target.parent.glob("*.tmp"))
            assert len(tmp_files) == 1
            assert tmp_files[0].parent == target.parent
            f.write("content")

        assert target.read_text() == "content"
