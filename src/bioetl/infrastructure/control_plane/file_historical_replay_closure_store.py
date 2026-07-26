"""File-backed persistence for historical replay closure artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileHistoricalReplayClosureStore"]


class _HistoricalReplayClosureReportLike(Protocol):
    @property
    def report_id(self) -> str: ...

    def to_dict(self) -> dict[str, object]: ...


@dataclass(slots=True)
class FileHistoricalReplayClosureStore:
    """Persist closure-report artifacts under the control-plane tree."""

    base_path: Path

    def save(self, report: _HistoricalReplayClosureReportLike) -> Path:
        self.base_path.mkdir(parents=True, exist_ok=True)
        path = self.base_path / f"{report.report_id}.json"
        atomic_write_text(
            path,
            json.dumps(report.to_dict(), indent=2, sort_keys=True),
        )
        return path
