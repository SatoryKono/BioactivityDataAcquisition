"""Port for pipeline/workflow run-report persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["RunReportStorePort"]


@runtime_checkable
class RunReportStorePort(Protocol):
    """Atomic UTF-8 text writes for run-report artifacts."""

    def mkdir(self, path: str) -> None:
        """Create ``path`` and parents."""
        ...

    def write_text(self, path: str, content: str) -> None:
        """Atomically replace ``path`` with UTF-8 text."""
        ...

    def read_text(self, path: str) -> str:
        """Read UTF-8 text from ``path``."""
        ...
