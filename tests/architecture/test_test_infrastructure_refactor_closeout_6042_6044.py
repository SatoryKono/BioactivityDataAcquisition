"""Closeout guards for test infrastructure refactor issues #6042 and #6044."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PROFILE = (
    ROOT / "reports" / "quality" / "test-bootstrap-fixture-scope-profile.json"
)
SUPPORT_MAP = ROOT / "reports" / "quality" / "test-support-helper-ownership-map.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_6042_bootstrap_profile_blocks_unproven_scope_widening() -> None:
    profile = _load_json(BOOTSTRAP_PROFILE)

    assert profile["schema_version"] == "test-bootstrap-fixture-scope-profile-v1"
    assert profile["issue"] == 6042
    assert profile["debt_budget_policy"] == "flat_or_decreasing_only"
    assert profile["result"]["status"] == "pass"
    assert profile["result"]["test_count"] >= 300
    assert profile["result"]["test_file_count"] == len(
        list((ROOT / "tests" / "unit" / "composition" / "bootstrap").rglob("test_*.py"))
    )
    assert profile["result"]["local_conftest_present"] is False

    policy = profile["fixture_scope_policy"]
    assert policy["broad_scope_changes_made"] is False
    assert policy["session_scope_allowed_without_isolation_proof"] is False
    assert policy["requires_state_isolation_proof"] is True
    assert "mutable service instances" in policy["blocked_session_scope_targets"]
    assert profile["closeout_decision"]["status"] == "closed-ready"


def test_issue_6044_support_helper_ownership_map_is_complete() -> None:
    support_map = _load_json(SUPPORT_MAP)

    assert support_map["schema_version"] == "test-support-helper-ownership-map-v1"
    assert support_map["issue"] == 6044
    assert support_map["debt_budget_policy"] == "flat_or_decreasing_only"

    modules = support_map["modules"]
    assert support_map["support_module_count"] == len(modules)
    assert support_map["support_module_count"] == len(
        list((ROOT / "tests" / "unit" / "application").rglob("*_test_support.py"))
    )

    allowed_decisions = {
        "retain_domain_helper",
        "retain_local_plugin",
        "retain_package_helper",
    }
    for module in modules:
        assert (ROOT / module["path"]).exists(), module["path"]
        assert module["decision"] in allowed_decisions
        assert module["owner_scope"]
        assert module["mutable_state"]
        assert module["consumers"], module["path"]
        for consumer in module["consumers"]:
            assert (ROOT / consumer).exists(), consumer

    policy = support_map["consolidation_policy"]
    assert policy["global_conftest_move_allowed"] is False
    assert policy["deduplicate_only_when_shared_semantics_match"] is True
    assert policy["requires_consumer_update_plan"] is True
    assert support_map["closeout_decision"]["status"] == "closed-ready"
