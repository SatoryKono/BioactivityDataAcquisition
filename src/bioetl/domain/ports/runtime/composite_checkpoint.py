"""Port for composite pipeline checkpoint persistence.

Decouples composite checkpoint service (application layer) from filesystem I/O,
following the same pattern as CheckpointPort for single-pipeline checkpoints.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CompositeCheckpointPort(Protocol):
    """Abstraction for composite checkpoint file storage.

    Implementations handle reading, writing, listing, and deleting
    checkpoint JSON blobs identified by composite name and run ID.
    """

    def read(self, path: str) -> str | None:
        """Read checkpoint content by relative path.

        Args:
            path: Relative checkpoint file path (e.g. ``composite_pub_run1.json``).

        Returns:
            File content as string, or None if not found.
        """
        ...

    def write_atomic(self, path: str, content: str) -> None:
        """Write checkpoint content atomically.

        Implementations must guarantee that partial writes are never visible
        to readers (e.g. write-to-temp + rename).

        Args:
            path: Relative checkpoint file path.
            content: JSON string to persist.
        """
        ...

    def delete(self, path: str) -> bool:
        """Delete a checkpoint file.

        Args:
            path: Relative checkpoint file path.

        Returns:
            True if file existed and was deleted, False if not found.
        """
        ...

    def list_glob(self, pattern: str) -> list[str]:
        """List checkpoint files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g. ``composite_publication_*.json``).

        Returns:
            List of matching relative paths, sorted by modification time descending.
        """
        ...

    def exists(self, path: str) -> bool:
        """Check if a checkpoint file exists.

        Args:
            path: Relative checkpoint file path.

        Returns:
            True if file exists.
        """
        ...
