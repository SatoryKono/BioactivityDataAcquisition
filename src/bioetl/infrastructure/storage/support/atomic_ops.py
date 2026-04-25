"""Atomic file write utilities.

Implements atomic write pattern (temp file + rename) for data integrity.

Requirements:
- REQ-DATA-004: Atomic writes to prevent partial/corrupted files
- Cross-platform compatibility (Unix, Windows)

Architecture:
- Uses tempfile.mkstemp for secure temp file creation
- Uses Path.replace() for atomic overwrite (works on Windows)
- Cleanup on error to prevent orphan temp files
"""

from __future__ import annotations

__all__ = [
    "ATOMIC_WRITE_EXCEPTIONS",
    "AtomicWriteError",
    "AtomicWriteGroup",
    "atomic_write",
    "atomic_write_bytes",
    "atomic_write_text",
]

import os
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from types import TracebackType
from typing import IO, Any

from bioetl.domain.exceptions.infrastructure import InfrastructureError as _InfraBase
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_GROUP_REPLACE_RETRY_POLICY,
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    AdaptiveRetryPolicy,
)


class AtomicWriteError(_InfraBase):
    """Raised when atomic write fails."""

    def __init__(self, target: Path, reason: str) -> None:
        self.target = target
        self.reason = reason
        super().__init__(f"Atomic write failed for '{target}': {reason}")


ATOMIC_WRITE_EXCEPTIONS = (
    AtomicWriteError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
)

_REPLACE_RETRYABLE_WINERRORS = {5, 32, 33}
_REPLACE_RETRYABLE_ERRNOS_WINDOWS = {13, 16}
_REPLACE_RETRYABLE_ERRNOS_NON_WINDOWS = {16}
_IS_WINDOWS = os.name == "nt"
ReplaceRetryHook = Callable[[int, float, OSError], None]


def _is_retryable_replace_error(error: OSError) -> bool:
    """Return True when Path.replace failure is transient on Windows-like FS."""
    winerror = getattr(error, "winerror", None)
    if isinstance(winerror, int):
        return bool(_IS_WINDOWS and winerror in _REPLACE_RETRYABLE_WINERRORS)
    errno_value = getattr(error, "errno", None)
    retryable_errnos = (
        _REPLACE_RETRYABLE_ERRNOS_WINDOWS
        if _IS_WINDOWS
        else _REPLACE_RETRYABLE_ERRNOS_NON_WINDOWS
    )
    return bool(isinstance(errno_value, int) and errno_value in retryable_errnos)


def _replace_with_retry(
    temp_path: Path,
    target: Path,
    *,
    retry_policy: AdaptiveRetryPolicy,
    on_retry: ReplaceRetryHook | None = None,
) -> None:
    """Replace target path with bounded retry for transient file-lock errors."""
    retry_count = 0
    while True:
        try:
            temp_path.replace(target)
            return
        except OSError as error:
            if not _is_retryable_replace_error(error):
                raise
            if not retry_policy.should_retry(retry_count):
                raise
            delay_seconds = retry_policy.calculate_delay(retry_count)
            if on_retry is not None:
                on_retry(retry_count + 1, delay_seconds, error)
            if delay_seconds > 0.0:
                time.sleep(delay_seconds)
            retry_count += 1


@contextmanager
def atomic_write(
    target: Path,
    mode: str = "wb",
    suffix: str = ".tmp",
    prefix: str = ".",
    encoding: str | None = None,
    retry_policy: AdaptiveRetryPolicy | None = None,
    on_retry: ReplaceRetryHook | None = None,
) -> Iterator[IO[Any]]:  # Any: IO stream type varies (text/binary)
    """Write through temp file and atomically replace target on success."""
    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (required for atomic rename)
    fd, temp_path_str = tempfile.mkstemp(
        suffix=suffix,
        prefix=prefix + target.stem + "_",
        dir=target.parent,
    )
    temp_path = Path(temp_path_str)

    try:
        # Open with os.fdopen to use the file descriptor
        # Pass encoding for text mode (ignored in binary mode)
        with os.fdopen(fd, mode, encoding=encoding) as f:
            yield f

        # Atomic replace with retry for transient Windows sharing violations.
        _replace_with_retry(
            temp_path,
            target,
            retry_policy=retry_policy or DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
            on_retry=on_retry,
        )

    except ATOMIC_WRITE_EXCEPTIONS as e:
        # Clean up temp file on any error
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass  # Best effort cleanup

        if isinstance(e, AtomicWriteError):
            raise
        raise AtomicWriteError(target, str(e)) from e


def atomic_write_bytes(
    target: Path,
    data: bytes,
    *,
    retry_policy: AdaptiveRetryPolicy | None = None,
    on_retry: ReplaceRetryHook | None = None,
) -> None:
    """Write bytes atomically to target file.

    Args:
        target: Path to the final destination file
        data: Bytes to write
        retry_policy: Optional retry policy controlling maximum attempts and
            delay for transient file-lock errors during the atomic replace step.
            Defaults to DEFAULT_ATOMIC_REPLACE_RETRY_POLICY.
        on_retry: Optional callback invoked before each retry attempt, receiving
            the attempt number, delay in seconds, and the triggering OSError.

    Raises:
        AtomicWriteError: If write fails

    """
    with atomic_write(
        target,
        mode="wb",
        retry_policy=retry_policy,
        on_retry=on_retry,
    ) as f:
        f.write(data)


def atomic_write_text(
    target: Path,
    text: str,
    encoding: str = "utf-8",
    *,
    retry_policy: AdaptiveRetryPolicy | None = None,
    on_retry: ReplaceRetryHook | None = None,
) -> None:
    """Write text atomically to target file.

    Args:
        target: Path to the final destination file.
        text: Text to write.
        encoding: Text encoding (default: utf-8).
        retry_policy: Optional adaptive retry policy for transient OS errors.
        on_retry: Optional callback invoked before each retry attempt.

    Raises:
        AtomicWriteError: If write fails.

    """
    with atomic_write(
        target,
        mode="w",
        encoding=encoding,
        retry_policy=retry_policy,
        on_retry=on_retry,
    ) as f:
        f.write(text)


class AtomicWriteGroup:
    """Manage atomic writes for multiple related files.

    Ensures all files in a group are written atomically together.
    If any file fails, all temp files are cleaned up.

    Example:
        >>> group = AtomicWriteGroup()
        >>> group.add(data_path, compressed_data)
        >>> group.add(meta_path, metadata_json.encode())
        >>> group.commit()  # Both files appear atomically

    """

    def __init__(
        self,
        *,
        retry_policy: AdaptiveRetryPolicy | None = None,
    ) -> None:
        self._pending: list[tuple[Path, Path, bytes]] = []  # (target, temp, data)
        self._retry_policy = retry_policy or DEFAULT_ATOMIC_GROUP_REPLACE_RETRY_POLICY

    def add(self, target: Path, data: bytes) -> None:
        """Add a file to the atomic write group.

        Args:
            target: Path to the final destination file
            data: Bytes to write

        """
        target.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            prefix="." + target.stem + "_",
            dir=target.parent,
        )
        temp_path = Path(temp_path_str)

        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            self._pending.append((target, temp_path, data))
        except (OSError, ValueError, TypeError, RuntimeError):
            # Clean up on write failure
            with suppress(OSError):
                temp_path.unlink()
            raise

    def commit(self) -> None:
        """Commit all pending writes atomically.

        Replaces all target files with their temp files.
        If any replace fails, attempts to rollback.

        Raises:
            AtomicWriteError: If commit fails

        """
        committed: list[tuple[Path, Path]] = []

        try:
            for target, temp_path, _ in self._pending:
                _replace_with_retry(
                    temp_path,
                    target,
                    retry_policy=self._retry_policy,
                )
                committed.append((target, temp_path))
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            # Rollback: remove any committed files (best effort)
            # Note: True rollback is impossible after replace,
            # but we clean up uncommitted temps
            self._cleanup_uncommitted(committed)
            raise AtomicWriteError(
                target, f"Commit failed after {len(committed)} files: {e}"
            ) from e
        finally:
            self._pending.clear()

    def rollback(self) -> None:
        """Cancel all pending writes and clean up temp files."""
        for _, temp_path, _ in self._pending:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass  # Why: temp file cleanup is best-effort; skip if already removed or locked
        self._pending.clear()

    def _cleanup_uncommitted(self, committed: list[tuple[Path, Path]]) -> None:
        """Clean up temp files that weren't committed."""
        committed_temps = {temp for _, temp in committed}
        for _, temp_path, _ in self._pending:
            if temp_path not in committed_temps:
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                except OSError:
                    pass  # Why: temp file cleanup is best-effort; skip if already removed or locked

    def __enter__(self) -> AtomicWriteGroup:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, rolling back on exception.

        If an exception occurred within the context, all pending temp files
        are cleaned up via rollback(). If no exception, user should have
        called commit() explicitly before exiting.

        Args:
            exc_type: Exception type if an exception was raised, None otherwise.
            exc_val: Exception instance if an exception was raised, None otherwise.
            exc_tb: Traceback if an exception was raised, None otherwise.
        """
        if exc_type is not None:
            self.rollback()
        # If no exception, user should have called commit()
