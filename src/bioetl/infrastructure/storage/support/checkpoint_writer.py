"""Filesystem-based composite checkpoint persistence.

Implements CompositeCheckpointPort for local filesystem storage with
atomic writes (write-to-temp + rename). Extracted from application layer
to satisfy ARCH-002 (no direct I/O in application/domain).
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path, PurePosixPath

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
        candidate = Path(checkpoint_dir)
        # POSIX-absolute roots (``/custom/...``) must not pick up a Windows drive.
        if candidate.as_posix().startswith("/") and not candidate.drive:
            self._checkpoint_dir = candidate
        else:
            self._checkpoint_dir = candidate.resolve()
        self._max_checkpoint_bytes = max_checkpoint_bytes
        self._max_glob_matches = max_glob_matches

    def _resolve_path(self, path: str) -> Path:
        """Resolve ``path`` under the checkpoint root; reject traversal escapes."""
        # Reject absolute / drive-qualified inputs (user-supplied relative only).
        if (
            not path or path.startswith(("/", "\\")) or ":" in path.split("/", 1)[0]
        ) and Path(path).is_absolute():
            raise CheckpointPathError(
                f"Checkpoint path must be relative to checkpoint root: {path!r}"
            )
        # Lexical ``is_relative_to`` does not collapse ``..``, so reject
        # traversal segments before joining (same rule as ``list_glob``).
        if ".." in Path(path).parts:
            raise CheckpointPathError(
                f"Checkpoint path escapes checkpoint root: {path!r}"
            )
        candidate = self._checkpoint_dir / path
        root_posix = PurePosixPath(self._checkpoint_dir.as_posix())
        candidate_posix = PurePosixPath(candidate.as_posix())
        if not candidate_posix.is_relative_to(root_posix):
            raise CheckpointPathError(
                f"Checkpoint path escapes checkpoint root: {path!r}"
            )
        if self._checkpoint_dir.drive:
            return candidate.resolve()
        return candidate

    def read(self, path: str) -> str | None:
        """Read checkpoint file content.

        Returns None if file does not exist or cannot be read.
        """
        full = self._resolve_path(path)
        if not full.exists():
            return None
        size = full.stat().st_size
        if size > self._max_checkpoint_bytes:
            raise CheckpointSizeError(
                f"Checkpoint file exceeds max size "
                f"({size} > {self._max_checkpoint_bytes}): {path!r}"
            )
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
        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            prefix=f".{full.stem}_",
            dir=full.parent,
        )
        temp = Path(temp_path_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            temp.replace(full)
        finally:
            if temp.exists():
                with contextlib.suppress(OSError):
                    temp.unlink()

    def delete(self, path: str) -> bool:
        """Delete checkpoint file. Returns True if existed."""
        full = self._resolve_path(path)
        if full.exists():
            full.unlink()
            return True
        return False

    def list_glob(self, pattern: str) -> list[str]:
        """List files matching glob, lexical descending by filename."""
        if not self._checkpoint_dir.exists():
            return []
        # Reject patterns that would escape via path segments.
        if ".." in Path(pattern).parts:
            raise CheckpointPathError(
                f"Checkpoint glob pattern must not contain '..': {pattern!r}"
            )
        matches = list(self._checkpoint_dir.glob(pattern))
        if len(matches) > self._max_glob_matches:
            raise CheckpointSizeError(
                f"Checkpoint glob matched {len(matches)} paths "
                f"(max {self._max_glob_matches}): {pattern!r}"
            )
        matches.sort(
            key=lambda p: p.name, reverse=True
        )  # deterministic lexical, not mtime
        return [p.name for p in matches]

    def exists(self, path: str) -> bool:
        """Check if checkpoint file exists."""
        return self._resolve_path(path).exists()
