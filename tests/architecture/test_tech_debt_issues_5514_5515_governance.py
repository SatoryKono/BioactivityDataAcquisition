# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Governance closeout guards for technical-debt issues #5514 and #5515."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.engineering.qa.report_flaky_test_burndown_review import build_payload

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
FLAKY_REVIEW = ROOT / "reports" / "quality" / "flaky-test-burndown-review.json"
FLAKY_INVENTORY = ROOT / "configs" / "quality" / "flaky_test_inventory.yaml"
TEST_GOVERNANCE = ROOT / "reports" / "quality" / "test-governance-current.json"
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


def test_issue_5514_flaky_test_burndown_review_matches_canonical_inputs() -> None:
    review = _load_json(FLAKY_REVIEW)
    test_governance = _load_json(TEST_GOVERNANCE)

    assert review == build_payload(ROOT)
    assert review["linked_issue"] == "#5514"
    assert review["decision"] == "reviewed_inventory_clear"
    assert review["source_artifacts"] == [
        "configs/quality/flaky_test_inventory.yaml",
        "reports/quality/test-governance-current.json",
    ]
    assert FLAKY_INVENTORY.exists()
    for relative_path in review["source_artifacts"]:
        assert (ROOT / relative_path).exists(), relative_path

    assert (
        review["summary"]["total_tests_analyzed"]
        == test_governance["report"]["total_test_functions"]
    )
    assert (
        review["source_fingerprints"]["test_governance_source_tree_sha256"]
        == test_governance["source_tree_sha256"]
    )
    assert review["summary"]["total_flaky"] == 0
    assert review["reviewed_flaky_tests"] == []


def test_issue_5515_runtime_cardinality_inventory_has_no_unused_event_debt() -> None:
    inventory = _load_json(RUNTIME_CARDINALITY_INVENTORY)
    runtime_review = _load_json(RUNTIME_CARDINALITY_REVIEW)

    assert inventory["unused_declared_observability_events"] == []
    assert inventory["unused_declared_metrics"] == []
    assert inventory["runtime_cardinality_review_required"] == []
    assert inventory["runtime_cardinality_threshold_violations"] == []
    assert runtime_review["review_required_metrics"] == []
