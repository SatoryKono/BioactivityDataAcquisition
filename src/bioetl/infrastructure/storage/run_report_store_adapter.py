"""Filesystem adapter for run-report artifact persistence."""

from __future__ import annotations

from pathlib import Path

from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunReportStoreAdapter"]


class FileRunReportStoreAdapter:
    """Persist run-report text artifacts through the storage atomic writer."""

    def mkdir(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    def write_text(self, path: str, content: str) -> None:
        target = Path(path)
        self.mkdir(str(target.parent))
        atomic_write_text(target, content)

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")
