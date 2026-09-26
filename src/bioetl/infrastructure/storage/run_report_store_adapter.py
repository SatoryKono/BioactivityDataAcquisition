"""Filesystem adapter for run-report artifact persistence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from bioetl.infrastructure.storage.atomic import atomic_write_text
from bioetl.infrastructure.storage.file_metadata_index import FileMetadataIndex

__all__ = ["FileRunReportStoreAdapter"]


def _identity_projection(raw: str) -> str:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return "{}"
    return json.dumps(
        {
            "identity": payload.get("identity"),
            "schema_version": payload.get("schema_version"),
        }
    )


_REPORT_IDENTITIES = FileMetadataIndex(_identity_projection)


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

    def read_identity_text(self, path: str) -> str:
        """Share compact identities across catalog readers, checking file freshness."""
        return _REPORT_IDENTITIES.read(Path(path))

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
