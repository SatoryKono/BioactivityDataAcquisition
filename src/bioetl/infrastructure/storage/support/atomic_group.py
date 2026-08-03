# basedpyright residual burn-down (shrink-only product surface).
"""Atomic multi-file write group implementation."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from types import TracebackType

from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_GROUP_REPLACE_RETRY_POLICY,
    AdaptiveRetryPolicy,
)
from bioetl.infrastructure.storage.support._atomic_replace import (
    AtomicWriteError,
    _replace_with_retry,
)


class AtomicWriteGroup:
    """Manage atomic writes for multiple related files."""

    def __init__(
        self,
        *,
        retry_policy: AdaptiveRetryPolicy | None = None,
    ) -> None:
        self._pending: list[tuple[Path, Path, bytes]] = []
        self._retry_policy = retry_policy or DEFAULT_ATOMIC_GROUP_REPLACE_RETRY_POLICY

    def add(self, target: Path, data: bytes) -> None:
        """Add a file to the atomic write group."""
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
            with suppress(OSError):
                temp_path.unlink()
            raise

    def commit(self) -> None:
        """Commit all pending writes atomically."""
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
            self._cleanup_uncommitted(committed)
            raise AtomicWriteError(
                target,
                f"Commit failed after {len(committed)} files: {e}",  # pyright: ignore[reportPossiblyUnboundVariable]
            ) from e
        finally:
            self._pending.clear()

    def rollback(self) -> None:
        """Cancel all pending writes and clean up temp files."""
        for _, temp_path, _ in self._pending:
            with suppress(OSError):
                if temp_path.exists():
                    temp_path.unlink()
        self._pending.clear()

    def _cleanup_uncommitted(self, committed: list[tuple[Path, Path]]) -> None:
        """Clean up temp files that were not committed."""
        committed_temps = {temp for _, temp in committed}
        for _, temp_path, _ in self._pending:
            if temp_path not in committed_temps:
                with suppress(OSError):
                    if temp_path.exists():
                        temp_path.unlink()

    def __enter__(self) -> AtomicWriteGroup:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, rolling back on exception."""
        if exc_type is not None:
            self.rollback()
