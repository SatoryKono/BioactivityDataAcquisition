"""Filesystem adapter for run-report artifact persistence."""

from __future__ import annotations

import shutil
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

    def is_file(self, path: str) -> bool:
        return Path(path).is_file()

    def is_dir(self, path: str) -> bool:
        target = Path(path)
        return target.is_dir() and not target.is_symlink()

    def iterdir(self, path: str) -> list[str]:
        return [str(child) for child in Path(path).iterdir()]

    def mtime(self, path: str) -> float:
        return Path(path).stat().st_mtime

    def remove_tree(self, path: str, *, root: str) -> None:
        target = Path(path)
        boundary = Path(root).resolve()
        if not target.parent.resolve().is_relative_to(boundary):
            raise ValueError("report directory escapes report root")
        if target.resolve() == boundary:
            raise ValueError("cannot remove report root")
        if target.is_symlink() or target.is_file():
            target.unlink(missing_ok=True)
        else:
            if not target.resolve().is_relative_to(boundary):
                raise ValueError("report directory escapes report root")
            shutil.rmtree(target)
