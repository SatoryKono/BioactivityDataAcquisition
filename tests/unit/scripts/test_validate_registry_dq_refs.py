"""Unit tests for registry↔DQ reference consistency helpers."""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.ci.validate_registry_dq_refs import _validate_entry


def test_validate_entry_reports_identity_mismatch(tmp_path: Path) -> None:
    """Mismatch between registry and DQ file should be blocking."""
    entry = {
        "identity": {
            "contract_version": "1.0.0",
            "dq_policy_ref": "chembl.dq.v1",
            "rule_bundle_version": "dq-rules.v1.0",
        },
        "dq_policy_ref": "chembl.dq.v1",
        "rule_bundle_version": "dq-rules.v1.0",
    }
    contract_data = {
        "contract_ref": "chembl.invalid",
        "contract_version": "1.0.0",
        "dq_policy_ref": "chembl.dq.v1",
        "rule_bundle_version": "dq-rules.v1.0",
    }
    issues = _validate_entry(
        contract_ref="chembl.activity",
        entry=entry,
        contract_data=contract_data,
        contract_path=tmp_path / "activity.yaml",
    )
    assert any(issue["severity"] == "blocking" for issue in issues)
    assert any("contract_ref mismatch" in issue["message"] for issue in issues)


def test_validate_entry_passes_for_aligned_payload(tmp_path: Path) -> None:
    """Aligned registry and DQ config should produce no issues."""
    entry = {
        "identity": {
            "contract_version": "1.0.0",
            "dq_policy_ref": "chembl.dq.v1",
            "rule_bundle_version": "dq-rules.v1.0",
        },
        "dq_policy_ref": "chembl.dq.v1",
        "rule_bundle_version": "dq-rules.v1.0",
    }
    contract_data = {
        "contract_ref": "chembl.activity",
        "contract_version": "1.0.0",
        "dq_policy_ref": "chembl.dq.v1",
        "rule_bundle_version": "dq-rules.v1.0",
    }
    issues = _validate_entry(
        contract_ref="chembl.activity",
        entry=entry,
        contract_data=contract_data,
        contract_path=tmp_path / "activity.yaml",
    )
    assert issues == []
