"""Filesystem-based composite checkpoint persistence.

Implements CompositeCheckpointPort for local filesystem storage with
atomic writes (write-to-temp + rename). Extracted from application layer
to satisfy ARCH-002 (no direct I/O in application/domain).
"""

from __future__ import annotations

from pathlib import Path


class FileCompositeCheckpointWriter:
    """Filesystem adapter for composite checkpoint persistence.

    Provides read, write, delete, list, and exists operations on
    checkpoint JSON files within a configured directory.
    """

    def __init__(self, checkpoint_dir: Path) -> None:
        self._checkpoint_dir = checkpoint_dir

    def read(self, path: str) -> str | None:
        """Read checkpoint file content.

        Returns None if file does not exist or cannot be read.
        """
        full = self._checkpoint_dir / path
        if not full.exists():
            return None
        return full.read_text()

    def write_atomic(self, path: str, content: str) -> None:
        """Write checkpoint file atomically via temp + rename."""
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        full = self._checkpoint_dir / path
        temp = full.with_suffix(".tmp")
        try:
            temp.write_text(content)
            temp.replace(full)
        finally:
            if temp.exists():
                temp.unlink()

    def delete(self, path: str) -> bool:
        """Delete checkpoint file. Returns True if existed."""
        full = self._checkpoint_dir / path
        if full.exists():
            full.unlink()
            return True
        return False

    def list_glob(self, pattern: str) -> list[str]:
        """List files matching glob, lexical descending by filename."""
        if not self._checkpoint_dir.exists():
            return []
        matches = list(self._checkpoint_dir.glob(pattern))
        matches.sort(key=lambda p: p.name, reverse=True)  # deterministic lexical, not mtime
        return [p.name for p in matches]

    def exists(self, path: str) -> bool:
        """Check if checkpoint file exists."""
        return (self._checkpoint_dir / path).exists()
