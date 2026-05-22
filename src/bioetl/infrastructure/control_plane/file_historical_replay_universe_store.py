"""File-backed persistence for historical replay universe artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileHistoricalReplayUniverseStore"]


class _HistoricalReplayUniverseClosureReportLike(Protocol):
    """Structural contract for persistable historical replay universe reports."""

    report_id: str

    def to_dict(self) -> dict[str, object]: ...


@dataclass(slots=True)
class FileHistoricalReplayUniverseStore:
    """Persist full-universe closure artifacts under the control-plane tree."""

    base_path: Path

    def save(self, report: _HistoricalReplayUniverseClosureReportLike) -> Path:
        self.base_path.mkdir(parents=True, exist_ok=True)
        path = self.base_path / f"{report.report_id}.json"
        atomic_write_text(
            path,
            json.dumps(report.to_dict(), indent=2, sort_keys=True),
        )
        return path

    def load_latest_report(self) -> dict[str, object] | None:
        """Return the newest persisted universe report payload, if any."""
        if not self.base_path.exists():
            return None
        candidates = sorted(
            self.base_path.glob("*.json"),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        for path in candidates:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("_artifact_path", str(path))
                return payload
        return None
