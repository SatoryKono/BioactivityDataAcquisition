"""Bounded filesystem path helpers for storage adapters."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

__all__ = [
    "DEFAULT_PATH_EXISTS_TIMEOUT_SECONDS",
    "path_exists_bounded",
]

DEFAULT_PATH_EXISTS_TIMEOUT_SECONDS = 5.0


def path_exists_bounded(
    path: Path | str,
    *,
    timeout_seconds: float = DEFAULT_PATH_EXISTS_TIMEOUT_SECONDS,
) -> bool:
    """Return whether ``path`` exists under a bounded I/O policy.

    Local ``Path.exists`` is offloaded so network/FUSE stalls cannot block the
    caller indefinitely. Timeouts and ``OSError`` map to ``False`` (defined
    failure: treat as not persisted rather than crashing the write path).
    """
    target = Path(path)
    if timeout_seconds <= 0:
        try:
            return target.exists()
        except OSError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(target.exists)
        try:
            return bool(future.result(timeout=timeout_seconds))
        except concurrent.futures.TimeoutError:
            return False
        except OSError:
            return False
