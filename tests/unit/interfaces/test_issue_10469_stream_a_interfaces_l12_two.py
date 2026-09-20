"""Stream A leftover L12 interface residuals for #10469 / #10516."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.interfaces.http._pipeline_run_report_display import (
    _shape_rejection_details,
)
from bioetl.interfaces.http import run_report_ops as report_ops


pytestmark = pytest.mark.unit


def test_shape_rejection_details_skips_non_list_and_non_dict_items() -> None:
    assert (
        _shape_rejection_details({"contract_summary": {"rejection_details": "nope"}})
        == []
    )
    rows = _shape_rejection_details(
        {
            "contract_summary": {
                "rejection_details": [
                    "skip",
                    {
                        "reason_code": "gold_filter_exclusion",
                        "field": "activity_id",
                        "count": 2,
                    },
                ]
            }
        }
    )
    assert rows[0]["reason_code"] == "gold_filter_exclusion"
    assert rows[0]["field"] == "activity_id"


def test_validated_artifact_paths_rejects_run_outside_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = {"n": 0}

    def _fake_is_relative_to(self: Path, other: Path) -> bool:
        seen["n"] += 1
        if seen["n"] == 1:
            return False
        return True

    monkeypatch.setattr(Path, "is_relative_to", _fake_is_relative_to)
    with pytest.raises(ValueError, match="outside the configured report root"):
        report_ops._validated_artifact_paths(
            "chembl_activity",
            "run-1",
            "pipeline_run_report_json",
            tmp_path,
        )


def test_validated_artifact_paths_rejects_artifact_outside_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fake_is_relative_to(self: Path, other: Path) -> bool:
        if self.name.startswith("pipeline-run-report"):
            return False
        return True

    monkeypatch.setattr(Path, "is_relative_to", _fake_is_relative_to)
    with pytest.raises(ValueError, match="outside the selected run"):
        report_ops._validated_artifact_paths(
            "chembl_activity",
            "run-1",
            "pipeline_run_report_json",
            tmp_path,
        )
