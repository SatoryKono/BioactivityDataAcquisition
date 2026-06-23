"""Tests for file-backed historical replay closure artifact storage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from bioetl.infrastructure.control_plane.file_historical_replay_closure_store import (
    FileHistoricalReplayClosureStore,
)


pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _ClosureReport:
    report_id: str
    verdict: str
    missing_runs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "verdict": self.verdict,
            "missing_runs": list(self.missing_runs),
        }


def test_file_historical_replay_closure_store_persists_json_report(
    tmp_path: Path,
) -> None:
    store = FileHistoricalReplayClosureStore(base_path=tmp_path / "closures")
    report = _ClosureReport(
        report_id="closure-001",
        verdict="ready",
        missing_runs=("run-a", "run-b"),
    )

    written_path = store.save(report)

    assert written_path == tmp_path / "closures" / "closure-001.json"
    assert written_path.exists()
    assert json.loads(written_path.read_text(encoding="utf-8")) == {
        "missing_runs": ["run-a", "run-b"],
        "report_id": "closure-001",
        "verdict": "ready",
    }
