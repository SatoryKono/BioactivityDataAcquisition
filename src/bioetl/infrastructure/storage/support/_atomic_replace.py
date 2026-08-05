"""Shared atomic-replace primitives for storage write helpers."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

from bioetl.domain.exceptions.storage import InfrastructureError as _InfraBase
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy

__all__ = [
    "ATOMIC_WRITE_EXCEPTIONS",
    "AtomicWriteError",
    "ReplaceRetryHook",
    "_replace_with_retry",
]


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
