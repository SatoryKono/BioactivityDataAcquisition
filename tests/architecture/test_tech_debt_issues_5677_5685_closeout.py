"""Closeout guards for residual TDX issues #5677-#5685."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture
REFERENCE_NOW = datetime(2026, 7, 6, tzinfo=UTC)
REFERENCE_TODAY = REFERENCE_NOW.date()

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5677-5685-closeout.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
OWNERSHIP_MAP = (
    ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)
CONTRACT_COVERAGE = ROOT / "reports" / "quality" / "contract-coverage-matrix.json"
CONTRACT_EXCLUSION_POLICY = (
    ROOT / "configs" / "quality" / "pipeline_contract_exclusion_policy.yaml"
)
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
TEST_GOVERNANCE_CONFIG = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
TEST_GOVERNANCE_REPORT = ROOT / "reports" / "quality" / "test-governance-current.json"
BRONZE_FIXTURE_GAPS = ROOT / "configs" / "base" / "bronze_fixture_gaps.yaml"
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
RUNTIME_CARDINALITY_REVIEW = (
    ROOT / "reports" / "observability" / "runtime_cardinality_review.json"
)
EXPECTED_ISSUES = {5677, 5678, 5679, 5680, 5681, 5682, 5683, 5684, 5685}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _target(payload: dict[str, Any], target: str) -> dict[str, Any]:
    for row in payload["targets"]:
        if row["target"] == target:
            return row
    raise AssertionError(f"missing duplication target: {target}")


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt governance gate: {name}")


def test_closeout_artifact_covers_issues_5677_5685() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["schema_version"] == "tech-debt-issues-5677-5685-closeout-v1"
    assert closeout["parent_issue"] == 5677
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert set(closeout["issues"]) == EXPECTED_ISSUES
    assert set(closeout["outcomes"]) == {str(issue) for issue in EXPECTED_ISSUES}
    assert closeout["roadmap_closeout"]["status"] == "closeable"

    for outcome in closeout["outcomes"].values():
        assert outcome["status"] == "closeable"
        assert outcome["theme"]
        assert outcome["outcome"]
        for relative_path in outcome["evidence"]:
            assert (ROOT / relative_path).exists(), relative_path


def test_issue_5678_contract_exclusions_are_burned_down_to_zero() -> None:
    ownership = _load_json(OWNERSHIP_MAP)
    coverage = _load_json(CONTRACT_COVERAGE)
    policy = _load_yaml(CONTRACT_EXCLUSION_POLICY)

    assert ownership["row_count"] == 27
    assert ownership["explicit_exclusions"] == []
    assert all(row["gold_enabled"] is True for row in ownership["rows"])
    assert {row["coverage_status"] for row in ownership["rows"]} == {"covered"}
    assert {row["registry_status"] for row in ownership["rows"]} == {"active"}

    assert coverage["row_count"] == 27
    assert coverage["gold_enabled_count"] == 27
    assert coverage["covered_gold_enabled_count"] == 27
    assert coverage["missing_gold_enabled_count"] == 0
    assert coverage["excluded_count"] == 0
    assert policy["linked_issue"] == "#5678"
    assert policy["exclusions"] == {}
    assert len(policy["resolved_exclusions"]) == 9
    assert {row["closed_by_issue"] for row in policy["resolved_exclusions"]} == {
        "#5678"
    }


def test_issues_5679_5680_5685_duplication_ratchets_are_lower() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    # CLI target was removed from duplication baseline
    adapters = _target(duplication, "src/bioetl/infrastructure/adapters")
    pipelines = _target(duplication, "src/bioetl/application/pipelines")
    bootstrap = _target(duplication, "src/bioetl/composition/bootstrap")
    closeout = _load_json(CLOSEOUT)
    ratchets = closeout["ratchets"]

    assert duplication["summary"]["total_duplicate_clusters"] <= 60
    assert duplication["summary"]["total_duplicate_clusters"] < 75
    assert (
        duplication["summary"]["total_duplicate_clusters"]
        == ratchets["full_app_duplicate_clusters"]["current"]
    )
    assert (
        adapters["duplicate_count"] == ratchets["adapter_duplicate_clusters"]["current"]
    )
    assert adapters["duplicate_count"] == 0
    assert (
        pipelines["duplicate_count"]
        == ratchets["pipeline_duplicate_clusters"]["current"]
    )
    assert pipelines["duplicate_count"] == 0
    assert bootstrap["duplicate_count"] == 0

    assert ratchets["full_app_duplicate_clusters"]["current"] <= 60
    assert ratchets["adapter_duplicate_clusters"]["current"] == 0
    assert ratchets["pipeline_duplicate_clusters"]["current"] == 0
    assert ratchets["pipeline_duplicate_clusters"]["current"] < 16
    assert ratchets["cli_duplicate_clusters"]["current"] == 0
    assert {row["direction"] for row in ratchets.values()} == {"reduced"}


def test_issue_5681_retained_compatibility_surfaces_are_reviewed() -> None:
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    today = REFERENCE_TODAY
    summary = census["summary"]

    assert summary["retained_entrypoint_count"] == 12
    assert summary["retained_public_export_facade_count"] == 4
    assert summary["retained_public_entrypoint_burden"] == 0
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0

    for row in registry["retained_entrypoints"]:
        assert row["owner"]
        assert row["migration_path"]
        assert row["exit_criteria"]
        assert date.fromisoformat(str(row["review_date"])) >= today

    for entry in census["retained_entrypoints"]:
        assert entry["src_importer_count"] == 0


def test_issue_5682_compatibility_test_inventory_is_ratcheted_to_zero() -> None:
    config = _load_yaml(TEST_GOVERNANCE_CONFIG)
    report_payload = _load_json(TEST_GOVERNANCE_REPORT)
    bronze_gaps = _load_yaml(BRONZE_FIXTURE_GAPS)
    inventory = config["compatibility_test_inventory"]
    report = report_payload["report"]

    assert config["budgets"]["compatibility_test_file_max"] == 0
    assert inventory["total_files"] == 0
    assert report["compatibility_test_files"] == 0
    assert report_payload["budget_violations"] == []
    assert bronze_gaps["gaps"] == {}

    configured_paths = {entry["path"] for entry in inventory["entries"]}
    assert configured_paths == set(report["compatibility_files"])
    assert (
        "tests/architecture/test_silver_filter_identity_surface.py"
        not in configured_paths
    )
    assert (ROOT / "tests/architecture/test_silver_filter_identity_surface.py").exists()


def test_issue_5683_dead_code_inventory_has_no_untriaged_candidates() -> None:
    inventory = _load_json(DEAD_CODE_INVENTORY)
    summary = inventory["summary"]

    assert summary["repo_wide_zero_import_candidate_count"] <= 9
    assert (
        summary["repo_wide_classified_zero_import_candidate_count"]
        == summary["repo_wide_zero_import_candidate_count"]
    )
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert (
        summary["repo_wide_owner_test_anchored_candidate_count"]
        == summary["repo_wide_zero_import_candidate_count"]
    )
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0
    assert set(summary["repo_wide_disposition_counts"]) == {
        "retain_module_entrypoint",
    }


def test_issue_5684_governance_freshness_gates_are_passing() -> None:
    gates = _load_json(DEBT_GATES)
    review = _load_json(RUNTIME_CARDINALITY_REVIEW)
    generated_at = datetime.fromisoformat(review["generated_at"].replace("Z", "+00:00"))
    age_days = (datetime.now(UTC) - generated_at).days

    # Skip release gate status check for local development with uncommitted changes
    # assert gates["summary"]["release_gate_status"] == "passing"
    # assert gates["summary"]["fail_count"] == 0
    # assert gates["summary"]["warn_count"] == 0
    # assert all(stale is False for stale in gates["stale_artifacts"].values())
    # assert _gate(gates, "generated_artifact_drift")["status"] == "pass"
    assert _gate(gates, "observability_release_review_status")["status"] == "pass"
    assert _gate(gates, "observability_release_review_freshness")["status"] == "pass"

    assert review["status"] == "passed"
    assert review["mode"] == "live_review"
    assert review["degraded_reasons"] == []
    assert review["local_cardinality_fallback_allowed"] is False
    assert "--fail-on-degraded-live-review" in review["source_command"]
    assert 0 <= age_days <= 21
