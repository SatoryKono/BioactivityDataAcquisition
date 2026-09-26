"""Port for pipeline/workflow run-report persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["RunReportStorePort"]


@runtime_checkable
class RunReportStorePort(Protocol):
    """Portable text persistence and discovery for run-report artifacts."""

    def mkdir(self, path: str) -> None:
        """Create ``path`` and parents."""
        ...

    def write_text(self, path: str, content: str) -> None:
        """Atomically replace ``path`` with UTF-8 text."""
        ...

    def read_text(self, path: str) -> str:
        """Read UTF-8 text from ``path``."""
        ...

    def is_file(self, path: str) -> bool:
        """Return whether an artifact exists as a file."""
        ...

    def is_dir(self, path: str) -> bool:
        """Return whether a traversable directory exists."""
        ...

    def iterdir(self, path: str) -> list[str]:
        """List immediate child locations."""
        ...

    def mtime(self, path: str) -> float:
        """Return an artifact modification timestamp in Unix seconds."""
        ...

    def remove_tree(self, path: str, *, root: str) -> None:
        """Remove an artifact directory confined to the supplied report root."""
        ...
