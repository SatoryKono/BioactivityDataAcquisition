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
"""Architecture closeout guards for issues #6220 through #6229."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports/quality/tech-debt-issues-6220-6229-closeout.json"
EXPECTED_ISSUES = {6220, 6221, 6222, 6224, 6225, 6226, 6227, 6229}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_6220_public_lazy_facades_are_fully_classified() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_yaml(ROOT / "configs/quality/public_lazy_facade_inventory.yaml")
    facades = inventory["facades"]

    ratchet = closeout["ratchets"]["public_lazy_facade_rows"]
    assert inventory["row_count"] == ratchet["current"]
    assert len(facades) == inventory["row_count"] <= ratchet["opening"]
    assert not [
        row for row in facades if not row.get("classification") or not row.get("owner")
    ]
    assert closeout["ratchets"]["unclassified_public_lazy_facades"]["current"] == 0


def test_issue_6221_config_compatibility_facade_has_zero_first_party_importers() -> (
    None
):
    closeout = _load_json(CLOSEOUT)
    census = _load_json(ROOT / "reports/quality/compatibility-importer-census.json")
    summary = census["summary"]

    assert (
        summary["config_root_src_importer_count"]
        == closeout["ratchets"]["config_root_src_importers"]["current"]
    )
    assert summary["config_root_src_importer_count"] == 0
    for symbol in census["config_root_facade"]["symbols"]:
        assert symbol["current_src_importer_count"] == 0
        assert symbol["max_src_importers"] == 0


def test_issue_6222_bootstrap_and_control_plane_ownership_are_violation_free() -> None:
    closeout = _load_json(CLOSEOUT)
    scorecard = _load_json(ROOT / "reports/quality/architecture-quality-scorecard.json")
    bootstrap_map = _load_yaml(
        ROOT / "configs/quality/composition_bootstrap_owner_map.yaml"
    )
    control_plane_policy = _load_yaml(
        ROOT / "configs/quality/control_plane_facade_import_policy.yaml"
    )

    assert (
        scorecard["metrics"]["layer_violations"]
        == closeout["ratchets"]["layer_violations"]["current"]
    )
    assert scorecard["metrics"]["layer_violations"] == 0
    assert bootstrap_map["policy_scope"] == "composition_bootstrap_owner_map"
    assert bootstrap_map["owner_graphs"]
    assert control_plane_policy["policy_scope"] == "control_plane_facade_import_policy"
    assert control_plane_policy["facades"]


def test_issue_6224_dead_code_review_has_no_untriaged_zero_import_candidates() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(ROOT / "reports/quality/dead-code-inventory.json")
    summary = inventory["summary"]

    assert (
        summary["repo_wide_untriaged_zero_import_candidate_count"]
        == closeout["ratchets"]["repo_wide_untriaged_zero_import_candidates"]["current"]
    )
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0
    assert summary["triaged_retained_without_owner_tests_count"] == 0


def test_issue_6225_aggregate_registry_and_classification_are_aligned() -> None:
    closeout = _load_json(CLOSEOUT)
    registry = _load_json(
        ROOT / "reports/quality/domain-aggregate-invariant-registry.json"
    )
    classification = _load_yaml(
        ROOT / "configs/quality/domain_aggregate_classification.yaml"
    )

    assert registry["summary"]["missing_source_paths"] == []
    assert registry["summary"]["missing_test_paths"] == []
    assert (
        closeout["ratchets"]["aggregate_registry_missing_source_paths"]["current"] == 0
    )
    assert {row["aggregate"] for row in classification["true_aggregates"]} == {
        row["aggregate"] for row in registry["aggregates"]
    }


def test_issue_6226_pipeline_config_contract_gates_are_blocker_free() -> None:
    closeout = _load_json(CLOSEOUT)
    ownership = _load_json(
        ROOT / "reports/quality/pipeline-config-contract-ownership-map.json"
    )
    dq = _load_json(ROOT / "reports/quality/contract-registry-dq-diagnostics.json")
    discrepancy = _load_json(ROOT / "reports/quality/config-discrepancy-baseline.json")

    assert (
        ownership["row_count"]
        == closeout["ratchets"]["pipeline_config_contract_rows"]["current"]
    )
    assert ownership["row_count"] == 27
    assert (
        dq["blocking_issue_count"]
        == closeout["ratchets"]["contract_registry_dq_blocking_issues"]["current"]
    )
    assert dq["blocking_issue_count"] == 0
    assert (
        discrepancy["metrics"]["inconsistent_parameter_count"]
        == closeout["ratchets"]["config_discrepancy_inconsistent_parameters"]["current"]
    )
    assert discrepancy["metrics"]["inconsistent_parameter_count"] == 0


def test_issue_6227_replay_identity_and_observability_drift_gates_are_zero() -> None:
    closeout = _load_json(CLOSEOUT)
    uuid_seams = _load_yaml(ROOT / "configs/quality/runtime_uuid_seams.yaml")
    cardinality = _load_json(
        ROOT / "reports/observability/runtime_cardinality_inventory.json"
    )
    bronze = _load_yaml(ROOT / "configs/base/bronze_fixture_gaps.yaml")
    vcr = _load_json(ROOT / "reports/quality/vcr-metadata-catalog.json")

    assert uuid_seams["seams"] == []
    assert closeout["ratchets"]["runtime_uuid4_seams"]["current"] == 0
    assert cardinality["runtime_cardinality_review_required"] == []
    assert cardinality["runtime_cardinality_threshold_violations"] == []
    assert cardinality["dashboarded_without_declaration"] == []
    assert cardinality["documented_without_registry"] == []
    assert bronze["gaps"] == {}
    assert vcr["totals"]["unowned_cassette_count"] == 0


def test_issue_6229_architecture_scan_hotspots_are_split_and_cache_backed() -> None:
    test_matrix = _load_yaml(ROOT / "configs/quality/test_matrix.yaml")
    shards = _load_yaml(ROOT / "configs/quality/pytest_shards.yaml")
    telemetry = _load_yaml(ROOT / "configs/quality/test_telemetry_baseline.yaml")
    slowest = _load_json(ROOT / "reports/test-telemetry/slowest-tests.json")

    probe = telemetry["slow_governance_cache_probe"]
    report_probe = probe["probes"][0]
    assert probe["lane_isolation"]["isolated"] is True
    assert float(report_probe["improvement_factor"]) > 1.0
    assert slowest["total_cases"] == telemetry["duration_telemetry"]["total_cases"]
    assert "architecture-fast-boundary" in str(test_matrix)
    assert "architecture-slow-governance" in str(test_matrix)
    assert "architecture-fast-boundary" in str(shards)
    assert "architecture-slow-governance" in str(shards)
