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
from contextlib import contextmanager
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

from bioetl.domain.exceptions.infrastructure import InfrastructureError as _InfraBase
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    AdaptiveRetryPolicy,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.support.atomic_group import AtomicWriteGroup


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


def __getattr__(name: str) -> object:
    """Lazily expose compatibility re-exports without creating import cycles."""
    if name == "AtomicWriteGroup":
        from bioetl.infrastructure.storage.support.atomic_group import AtomicWriteGroup

        return AtomicWriteGroup
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
