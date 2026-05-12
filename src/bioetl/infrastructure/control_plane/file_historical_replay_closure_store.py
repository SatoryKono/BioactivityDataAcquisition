"""File-backed persistence for historical replay closure artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bioetl.application.services.control_plane.historical_replay_closure_service import (
    HistoricalReplayClosureReport,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileHistoricalReplayClosureStore"]


@dataclass(slots=True)
class FileHistoricalReplayClosureStore:
    """Persist closure-report artifacts under the control-plane tree."""

    base_path: Path

    def save(self, report: HistoricalReplayClosureReport) -> Path:
        self.base_path.mkdir(parents=True, exist_ok=True)
        path = self.base_path / f"{report.report_id}.json"
        atomic_write_text(
            path,
            json.dumps(report.to_dict(), indent=2, sort_keys=True),
        )
        return path
