"""Filesystem adapter for run-report artifact persistence."""

from __future__ import annotations

from pathlib import Path

from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunReportStoreAdapter"]


class FileRunReportStoreAdapter:
    """Persist run-report text artifacts through the storage atomic writer."""

    def mkdir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def write_text(self, path: Path, content: str) -> None:
        self.mkdir(path.parent)
        atomic_write_text(path, content)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")
