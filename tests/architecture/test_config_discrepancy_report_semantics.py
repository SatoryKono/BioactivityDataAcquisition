"""Semantic guardrails for config discrepancy reporting terminology."""

from __future__ import annotations

import pytest

import json
from pathlib import Path

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "docs" / "config-discrepancies-report.md"
BASELINE_PATH = ROOT / "reports" / "quality" / "config-discrepancy-baseline.json"


def test_config_discrepancy_report_separates_actionable_drift_from_sanctioned_variance() -> (
    None
):
    report = REPORT_PATH.read_text(encoding="utf-8")
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    metrics = baseline["metrics"]

    assert "## Actionable Drift Parameters" in report
    assert "## Sanctioned Partial Variance Parameters" in report
    assert "## Inconsistent Parameters" not in report

    assert (
        f"Actionable inconsistent parameters: "
        f"{metrics['inconsistent_parameter_count']}"
    ) in report
    assert (
        f"Sanctioned partial variance parameters: "
        f"{metrics['sanctioned_partial_parameter_count']}"
    ) in report
    assert f"Raw partial parameter count: {metrics['raw_inconsistent_parameter_count']}" in report

    if metrics["inconsistent_parameter_count"] == 0:
        assert "No unsanctioned config drift detected." in report
    if metrics["sanctioned_partial_parameter_count"] > 0:
        assert (
            "intentionally partial across governed config families"
            in report
        )

    assert "- CI should fail on actionable drift." in report
    assert "merge blocker" in report
