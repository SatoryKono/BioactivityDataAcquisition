"""Filesystem-based composite checkpoint persistence.

Implements CompositeCheckpointPort for local filesystem storage with
atomic writes (write-to-temp + rename). Extracted from application layer
to satisfy ARCH-002 (no direct I/O in application/domain).
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

# Bound checkpoint I/O to protect operators from oversized / runaway listings.
_DEFAULT_MAX_CHECKPOINT_BYTES = 16 * 1024 * 1024  # 16 MiB
_DEFAULT_MAX_GLOB_MATCHES = 10_000


class CheckpointPathError(ValueError):
    """Raised when a checkpoint path escapes the configured root."""


class CheckpointSizeError(ValueError):
    """Raised when a checkpoint payload exceeds the configured size budget."""


class FileCompositeCheckpointWriter:
    """Filesystem adapter for composite checkpoint persistence.

    Provides read, write, delete, list, and exists operations on
    checkpoint JSON files within a configured directory.
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        *,
        max_checkpoint_bytes: int = _DEFAULT_MAX_CHECKPOINT_BYTES,
        max_glob_matches: int = _DEFAULT_MAX_GLOB_MATCHES,
    ) -> None:
        self._checkpoint_dir = Path(checkpoint_dir).resolve(strict=False)
        self._max_checkpoint_bytes = max_checkpoint_bytes
        self._max_glob_matches = max_glob_matches

    @staticmethod
    def _relative_path(path: str, *, kind: str = "path") -> Path:
        """Return a normalized relative path or reject cross-platform escapes."""
        normalized = path.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        windows_path = PureWindowsPath(path)
        if (
            not path
            or posix_path.is_absolute()
            or bool(windows_path.drive)
            or bool(windows_path.root)
        ):
            raise CheckpointPathError(
                f"Checkpoint {kind} must be relative to checkpoint root: {path!r}"
            )
        if ".." in posix_path.parts or ".." in windows_path.parts:
            raise CheckpointPathError(
                f"Checkpoint {kind} escapes checkpoint root: {path!r}"
            )
        return Path(*posix_path.parts)

    def _ensure_contained(self, candidate: Path, *, source: str) -> Path:
        """Resolve ``candidate`` and require it to remain under the resolved root."""
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self._checkpoint_dir):
            raise CheckpointPathError(
                f"Checkpoint path escapes checkpoint root: {source!r}"
            )
        return resolved

    def _resolve_path(self, path: str) -> Path:
        """Resolve ``path`` under the checkpoint root; reject traversal escapes."""
        relative = self._relative_path(path)
        return self._ensure_contained(self._checkpoint_dir / relative, source=path)

    def read(self, path: str) -> str | None:
        """Read checkpoint file content.

        Returns None if file does not exist or cannot be read.
        """
        full = self._resolve_path(path)
        full = self._ensure_contained(full, source=path)
        if not full.exists():
            return None
        full = self._ensure_contained(full, source=path)
        size = full.stat().st_size
        if size > self._max_checkpoint_bytes:
            raise CheckpointSizeError(
                f"Checkpoint file exceeds max size "
                f"({size} > {self._max_checkpoint_bytes}): {path!r}"
            )
        full = self._ensure_contained(full, source=path)
        return full.read_text(encoding="utf-8")

    def write_atomic(self, path: str, content: str) -> None:
        """Write checkpoint file atomically via unique temp + rename."""
        encoded = content.encode("utf-8")
        if len(encoded) > self._max_checkpoint_bytes:
            raise CheckpointSizeError(
                f"Checkpoint payload exceeds max size "
                f"({len(encoded)} > {self._max_checkpoint_bytes}): {path!r}"
            )
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        full = self._resolve_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full = self._ensure_contained(full, source=path)
        parent = self._ensure_contained(full.parent, source=path)
        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            prefix=f".{full.stem}_",
            dir=parent,
        )
        temp = Path(temp_path_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            temp = self._ensure_contained(temp, source=path)
            full = self._ensure_contained(full, source=path)
            temp.replace(full)
        finally:
            with contextlib.suppress(OSError, CheckpointPathError):
                temp = self._ensure_contained(temp, source=path)
                if temp.exists():
                    temp.unlink()

    def delete(self, path: str) -> bool:
        """Delete checkpoint file. Returns True if existed."""
        full = self._resolve_path(path)
        full = self._ensure_contained(full, source=path)
        if full.exists():
            full = self._ensure_contained(full, source=path)
            full.unlink()
            return True
        return False

    def list_glob(self, pattern: str) -> list[str]:
        """List files matching glob, lexical descending by filename."""
        if not self._checkpoint_dir.exists():
            return []
        relative_pattern = self._relative_path(pattern, kind="glob pattern")
        matches = list(self._checkpoint_dir.glob(relative_pattern.as_posix()))
        if len(matches) > self._max_glob_matches:
            raise CheckpointSizeError(
                f"Checkpoint glob matched {len(matches)} paths "
                f"(max {self._max_glob_matches}): {pattern!r}"
            )
        matches = [self._ensure_contained(match, source=pattern) for match in matches]
        matches.sort(
            key=lambda p: p.name, reverse=True
        )  # deterministic lexical, not mtime
        return [p.name for p in matches]

    def exists(self, path: str) -> bool:
        """Check if checkpoint file exists."""
        full = self._resolve_path(path)
        return self._ensure_contained(full, source=path).exists()
