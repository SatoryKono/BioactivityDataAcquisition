"""Unit tests for architecture quality scorecard aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)

ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.unit


def test_architecture_quality_scorecard_has_stable_weighted_shape() -> None:
    payload = build_architecture_quality_scorecard(repo_root=ROOT)

    assert payload["schema_version"] == 1
    assert payload["weights_sum"] == 1.0
    assert len(payload["categories"]) == 10
    assert payload["integral_score"] == 7.98
    assert payload["interpretation"] == "satisfactory_system_refactoring_required"


def test_architecture_quality_scorecard_carries_live_evidence_metrics() -> None:
    payload = build_architecture_quality_scorecard(repo_root=ROOT)
    metrics = payload["metrics"]

    assert metrics["layer_violations"] == 0
    assert metrics["retained_entrypoint_count"] >= 0
    assert metrics["unmeasured_module_count"] >= 0
    assert metrics["contract_blocking_issue_count"] == 0
    assert metrics["dq_blocking_issue_count"] == 0
