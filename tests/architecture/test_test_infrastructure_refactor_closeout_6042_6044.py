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
    """Bootstrap profile stays live-topology-bound (#6042 remainder / #6892)."""
    profile = _load_json(BOOTSTRAP_PROFILE)
    bootstrap_root = ROOT / "tests" / "unit" / "composition" / "bootstrap"
    local_conftest = bootstrap_root / "conftest.py"
    isolation_proof = bootstrap_root / "test_bootstrap_metadata_cache_isolation.py"

    assert profile["schema_version"] == "test-bootstrap-fixture-scope-profile-v1"
    assert profile["issue"] in {6042, 6892}
    assert profile["debt_budget_policy"] == "flat_or_decreasing_only"
    assert profile["result"]["status"] == "pass"
    assert profile["result"]["test_count"] >= 300
    assert profile["result"]["test_file_count"] == len(
        list(bootstrap_root.rglob("test_*.py"))
    )

    # Live topology parity: do not hard-code a stale local_conftest_present
    # literal. The profile must match the filesystem.
    assert local_conftest.is_file()
    assert profile["result"]["local_conftest_present"] is True
    assert profile["result"]["local_conftest_path"] == (
        "tests/unit/composition/bootstrap/conftest.py"
    )
    assert isolation_proof.is_file()
    assert profile["result"]["isolation_proof"] == (
        "tests/unit/composition/bootstrap/test_bootstrap_metadata_cache_isolation.py"
    )

    conftest_text = local_conftest.read_text(encoding="utf-8")
    assert 'scope="session"' in conftest_text
    assert "bootstrap_metadata_cache" in conftest_text
    assert "cached_bootstrap_metadata" in conftest_text
    assert "fresh_pipeline_registry" in conftest_text
    assert "fresh_provider_registry" in conftest_text
    assert set(profile["result"]["session_scoped_immutable_fixtures"]) == {
        "bootstrap_metadata_cache",
        "cached_bootstrap_metadata",
    }
    assert set(profile["result"]["function_scoped_mutable_clones"]) == {
        "fresh_pipeline_registry",
        "fresh_provider_registry",
    }

    policy = profile["fixture_scope_policy"]
    assert policy["broad_scope_changes_made"] is False
    assert policy["session_scope_allowed_without_isolation_proof"] is False
    assert policy["requires_state_isolation_proof"] is True
    assert policy["session_scope_isolation_proven"] is True
    assert "mutable service instances" in policy["blocked_session_scope_targets"]
    assert profile["closeout_decision"]["status"] == "closed-ready"
    assert profile["closeout_decision"]["decision"] == (
        "session_immutable_catalog_cache_with_per_test_clones"
    )


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
