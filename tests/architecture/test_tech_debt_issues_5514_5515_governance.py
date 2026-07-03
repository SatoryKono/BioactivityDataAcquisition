"""Governance closeout guards for technical-debt issues #5514 and #5515."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
FLAKY_REVIEW = ROOT / "reports" / "quality" / "flaky-test-burndown-review.json"
FLAKINESS_DB = ROOT / "reports" / "test-swarm" / "SWARM-001" / "flakiness-database.json"
RUNTIME_CARDINALITY_INVENTORY = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
RUNTIME_CARDINALITY_REVIEW = (
    ROOT / "reports" / "observability" / "runtime_cardinality_review.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def test_issue_5514_flaky_test_burndown_review_matches_swarm_telemetry() -> None:
    review = _load_json(FLAKY_REVIEW)
    source = _load_json(FLAKINESS_DB)

    assert review["linked_issue"] == "#5514"
    assert review["decision"] == "closeable_zero_residual_flaky_tests"
    for relative_path in review["source_artifacts"]:
        assert (ROOT / relative_path).exists(), relative_path

    assert review["summary"]["total_tests_analyzed"] == source["total_tests_analyzed"]
    assert review["summary"]["total_flaky"] == source["summary"]["total_flaky"]
    assert review["summary"]["by_layer"] == source["summary"]["by_layer"]
    assert review["summary"]["by_category"] == source["summary"]["by_category"]
    assert review["summary"]["by_severity"] == source["summary"]["by_severity"]
    assert review["summary"]["by_triage"] == source["summary"]["by_triage"]
    assert review["summary"]["by_alert_level"] == source["summary"]["by_alert_level"]
    assert review["reviewed_flaky_tests"] == source["flaky_tests"] == []


def test_issue_5515_runtime_cardinality_inventory_has_no_unused_event_debt() -> None:
    inventory = _load_json(RUNTIME_CARDINALITY_INVENTORY)
    runtime_review = _load_json(RUNTIME_CARDINALITY_REVIEW)

    assert inventory["unused_declared_observability_events"] == []
    assert inventory["unused_declared_metrics"] == []
    assert inventory["runtime_cardinality_review_required"] == []
    assert inventory["runtime_cardinality_threshold_violations"] == []
    assert runtime_review["review_required_metrics"] == []
