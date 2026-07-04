"""Closeout guards for governance quality issues #5933, #5937, #5938, #5942-#5944."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.interfaces.cli.commands.quarantine import (
    SILVER_FILTER_ALIAS_HELP,
    SILVER_FILTER_ALIAS_SUNSET_DATE,
    SILVER_FILTER_ERROR_CODE,
)
from bioetl.interfaces.http.control_plane_identity.types import (
    IDENTITY_EVIDENCE_CONTRACT,
    AnchorSpec,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5933-5944-closeout.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
SCORECARD = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
REMOTE_BASELINE = (
    ROOT / "reports" / "quality" / "architecture-debt-remote-main-baseline.json"
)
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
RUNTIME_CARDINALITY_INVENTORY = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
RUNTIME_CARDINALITY_REVIEW = (
    ROOT / "reports" / "observability" / "runtime_cardinality_review.json"
)
CONFIG_DISCREPANCY = ROOT / "reports" / "quality" / "config-discrepancy-baseline.json"
CONTRACT_COVERAGE = ROOT / "reports" / "quality" / "contract-coverage-matrix.json"
CONFIG_COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "config_compatibility_registry.yaml"
)
TEST_GOVERNANCE = ROOT / "reports" / "quality" / "test-governance-current.json"
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
EXPECTED_ISSUES = {5933, 5937, 5938, 5942, 5943, 5944}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt governance gate: {name}")


def _duplication_target(payload: dict[str, Any], target: str) -> dict[str, Any]:
    for row in payload["targets"]:
        if row["target"] == target:
            return row
    raise AssertionError(f"missing duplication target: {target}")


def test_closeout_artifact_is_complete_and_budget_safe() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["schema_version"] == "tech-debt-issues-5933-5944-closeout-v1"
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert closeout["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in closeout["issues"]} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in closeout["issues"])
    assert set(closeout["outcomes"]) == {str(issue) for issue in EXPECTED_ISSUES}
    assert all(
        outcome["status"] == "closeable" for outcome in closeout["outcomes"].values()
    )

    for issue in closeout["issues"]:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), relative_path

    for metric_name, ratchet in closeout["ratchets"].items():
        assert ratchet["current"] <= ratchet["max"], metric_name
        assert (ROOT / ratchet["source"]).exists(), metric_name


def test_issue_5933_governance_artifacts_are_rebaselined() -> None:
    closeout = _load_json(CLOSEOUT)
    gates = _load_json(DEBT_GATES)
    coverage = _load_json(MODULE_COVERAGE)
    scorecard = _load_json(SCORECARD)
    duplication = _load_json(DUPLICATION_BASELINE)
    remote = _load_json(REMOTE_BASELINE)
    debt_scorecard = _load_yaml(DEBT_SCORECARD)

    assert gates["summary"]["release_gate_status"] == "passing"
    assert gates["summary"]["fail_count"] == 0
    assert gates["summary"]["warn_count"] == 0
    assert all(stale is False for stale in gates["stale_artifacts"].values())

    coverage_summary = coverage["summary"]
    assert (
        coverage_summary["source_module_count"]
        == closeout["metrics"]["source_module_count"]["current"]
    )
    assert coverage_summary["uncovered_module_count"] == 0
    assert coverage_summary["unmeasured_module_count"] == 0
    assert (
        coverage["source_tree_sha256"]
        == closeout["metrics"]["source_tree_sha256"]["current"]
    )
    assert (
        scorecard["source_artifacts"]["module_coverage_inventory"]["source_tree_sha256"]
        == coverage["source_tree_sha256"]
    )
    assert (
        scorecard["integral_score"]
        == closeout["metrics"]["architecture_quality_score"]["current"]
    )
    assert (
        scorecard["metrics"]["source_module_count"]
        == coverage_summary["source_module_count"]
    )

    targets = {row["target"]: row["duplicate_count"] for row in duplication["targets"]}
    assert (
        duplication["summary"]["total_duplicate_clusters"]
        == closeout["ratchets"]["full_app_duplicate_clusters"]["current"]
    )
    assert (
        targets["src/bioetl/infrastructure/adapters"]
        == closeout["ratchets"]["infrastructure_adapter_duplicate_clusters"]["current"]
    )
    assert (
        targets["src/bioetl/application/pipelines"]
        == closeout["ratchets"]["application_pipeline_duplicate_clusters"]["current"]
    )
    assert targets["src/bioetl/composition/bootstrap"] == 0
    assert targets["src/bioetl/interfaces/cli"] == 0

    scorecard_ratchets = debt_scorecard["full_app_duplication_ratchets"]
    families = {row["name"]: row for row in scorecard_ratchets["families"]}
    assert (
        families["infrastructure_adapters"]["metrics"]["duplication_clusters"][
            "current_count"
        ]
        == targets["src/bioetl/infrastructure/adapters"]
    )
    assert (
        families["infrastructure_adapters"]["metrics"]["duplication_clusters"][
            "max_count"
        ]
        == targets["src/bioetl/infrastructure/adapters"]
    )
    assert (
        scorecard_ratchets["summary_metrics"]["total_duplicate_clusters"][
            "current_count"
        ]
        == duplication["summary"]["total_duplicate_clusters"]
    )
    assert (
        scorecard_ratchets["summary_metrics"]["total_duplicate_clusters"]["max_count"]
        == duplication["summary"]["total_duplicate_clusters"]
    )

    assert remote["local_tracking_ref_matches_remote"] is True
    missing_rows = [
        row for row in remote["artifacts"] if not row["summary"].get("available")
    ]
    assert missing_rows
    assert all(row["introduced_after_remote_main"] is True for row in missing_rows)
    assert all(row["required_on_remote"] is False for row in missing_rows)
    assert not [
        row
        for row in remote["artifacts"]
        if row["required_on_remote"] and not row["summary"].get("available")
    ]

    baseline_source = (
        ROOT / "scripts/engineering/qa/report_architecture_debt_remote_main_baseline.py"
    ).read_text(encoding="utf-8")
    gates_source = (
        ROOT / "scripts/engineering/qa/report_debt_governance_gates.py"
    ).read_text(encoding="utf-8")
    assert "introduced_after_remote_main" in baseline_source
    assert "required_on_remote" in baseline_source
    assert "_unavailable_required_remote_baseline_artifacts" in gates_source


def test_issue_5938_silver_filter_alias_is_sunset_ready() -> None:
    quarantine_tests = (
        ROOT / "tests/unit/interfaces/cli/commands/test_quarantine.py"
    ).read_text(encoding="utf-8")
    runbook = (ROOT / "docs/05-operations/runbooks/quarantine-management.md").read_text(
        encoding="utf-8"
    )
    cli_reference = (ROOT / "docs/04-reference/cli.md").read_text(encoding="utf-8")

    assert SILVER_FILTER_ERROR_CODE == "FILTERED_OUT_SILVER"
    assert SILVER_FILTER_ALIAS_SUNSET_DATE == "2026-09-30"
    assert "Deprecated legacy alias" in SILVER_FILTER_ALIAS_HELP
    assert "sunset 2026-09-30" in SILVER_FILTER_ALIAS_HELP
    assert "FILTERED_OUT_SILVER" in SILVER_FILTER_ALIAS_HELP
    assert "Silver structural rejects only" in SILVER_FILTER_ALIAS_HELP
    assert "not Gold" in SILVER_FILTER_ALIAS_HELP

    assert "--silver-filter-only" in quarantine_tests
    assert "FILTERED_OUT_SILVER" in quarantine_tests
    assert "--silver-filter-only" in runbook
    assert "2026-09-30" in runbook
    assert "--error-code FILTERED_OUT_SILVER" in runbook
    assert "not Gold" in runbook
    assert "--silver-filter-only" in cli_reference
    assert "sunset 2026-09-30" in cli_reference


def test_issue_5937_control_plane_identity_legacy_aliases_are_bounded() -> None:
    source = (
        ROOT / "src/bioetl/interfaces/http/control_plane_identity/types.py"
    ).read_text(encoding="utf-8")

    assert IDENTITY_EVIDENCE_CONTRACT == "control_plane_identity_evidence_v1"
    assert "sunset date: 2026-12-31" in source

    canonical = AnchorSpec(
        priority="primary",
        name="manifest_id",
        label="Manifest ID",
        source="run_manifest",
        value_format="string",
        why="stable run identity",
        rendering="copyable",
        copy=True,
        drilldown="/runs/{manifest_id}",
        missing_severity="INFO",
    )
    assert canonical.anchor_name == "manifest_id"
    assert canonical.display_name == "Manifest ID"
    assert canonical.source_location == "run_manifest"
    assert canonical.data_type == "string"
    assert canonical.description == "stable run identity"
    assert canonical.display_mode == "copyable"
    assert canonical.is_identifier is True
    assert canonical.usage_locations == "/runs/{manifest_id}"
    assert canonical.implementation_status == "SHIPPED"

    legacy = AnchorSpec(
        priority="primary",
        anchor_name="run_id",
        display_name="Run ID",
        source_location="ledger",
        data_type="string",
        description="legacy run identity",
        display_mode="text",
        is_identifier=True,
        usage_locations="/ledger/{run_id}",
        implementation_status="SHIPPED",
    )
    assert legacy.name == "run_id"
    assert legacy.label == "Run ID"
    assert legacy.source == "ledger"
    assert legacy.value_format == "string"
    assert legacy.why == "legacy run identity"
    assert legacy.rendering == "text"
    assert legacy.copy is True
    assert legacy.drilldown == "/ledger/{run_id}"
    assert legacy.missing_severity == "INFO"
    assert legacy.implementation_status == "SHIPPED"


def test_issue_5942_observability_runtime_cardinality_is_clean() -> None:
    gates = _load_json(DEBT_GATES)
    inventory = _load_json(RUNTIME_CARDINALITY_INVENTORY)
    review = _load_json(RUNTIME_CARDINALITY_REVIEW)

    assert review["status"] == "passed"
    assert review["review_required_metrics"] == []
    assert review["static_threshold_violations"] == []
    assert review["local_threshold_violations"] == []
    assert review["live_threshold_violations"] == []
    assert review["degraded_reasons"] == []
    assert review["query_errors"] == {}

    assert inventory["dashboarded_without_emission"] == []
    assert inventory["dashboarded_without_declaration"] == []
    assert inventory["declared_risky_label_review_required"] == []
    assert (
        _gate(gates, "observability_dashboarded_without_emission")["status"] == "pass"
    )
    assert (
        _gate(gates, "observability_runtime_cardinality_review_required")["status"]
        == "pass"
    )
    assert (
        _gate(gates, "observability_runtime_cardinality_threshold_violations")["status"]
        == "pass"
    )
    assert _gate(gates, "observability_release_review_status")["status"] == "pass"


def test_issue_5943_config_compatibility_and_contracts_are_clean() -> None:
    discrepancy = _load_json(CONFIG_DISCREPANCY)
    coverage = _load_json(CONTRACT_COVERAGE)
    registry = _load_yaml(CONFIG_COMPATIBILITY_REGISTRY)

    metrics = discrepancy["metrics"]
    assert metrics["config_count"] == 27
    assert metrics["unique_parameter_count"] == 419
    assert metrics["inconsistent_parameter_count"] == 0
    assert metrics["raw_inconsistent_parameter_count"] == 0
    assert metrics["sanctioned_partial_parameter_count"] == 0

    assert coverage["row_count"] == 27
    assert coverage["covered_gold_enabled_count"] == 27
    assert coverage["missing_gold_enabled_count"] == 0
    assert coverage["constraint_completeness_missing_count"] == 0
    assert coverage["constraint_completeness_review_count"] == 27
    assert coverage["golden_test_evidence_count"] == 27

    burn_down = registry["policy"]["burn_down"]
    assert len(registry["accepted_shapes"]) <= burn_down["accepted_shape_max"]
    assert (
        len(registry.get("migration_supported_shapes", []))
        <= burn_down["migration_supported_shape_max"]
    )
    assert (
        len(registry["retired_rejected_shapes"])
        >= burn_down["retired_rejected_shape_min"]
    )
    assert burn_down["expired_shape_policy"] == "fail-ci"

    for row in registry["accepted_shapes"] + registry["retired_rejected_shapes"]:
        for relative_path in row["source_files"] + row["test_files"]:
            assert (ROOT / relative_path).exists(), (row["id"], relative_path)


def test_issue_5944_test_governance_closeout_metrics_are_clean() -> None:
    test_governance = _load_json(TEST_GOVERNANCE)
    dead_code = _load_json(DEAD_CODE_INVENTORY)
    compatibility = _load_json(COMPATIBILITY_CENSUS)
    coverage = _load_json(MODULE_COVERAGE)

    summary = test_governance["summary"]
    assert summary["compatibility_test_files"] == 0
    assert summary["markerless_test_functions"] == 0
    assert summary["refined_assertless_tests"] == 0
    assert summary["uuid4_call_sites"] == 0
    assert summary["date_today_call_sites"] == 0
    assert summary["duplicate_test_names"] == 1
    assert summary["duplicate_test_name_occurrences"] == 2
    assert test_governance["budget_violations"] == []

    dead_summary = dead_code["summary"]
    assert dead_summary["repo_wide_zero_import_candidate_count"] == 9
    assert dead_summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert dead_summary["repo_wide_candidates_without_owner_tests_count"] == 0
    assert dead_summary["repo_wide_owner_test_anchored_candidate_count"] == 9

    compatibility_summary = compatibility["summary"]
    assert compatibility_summary["retained_entrypoint_count"] == 12
    assert compatibility_summary["retained_public_entrypoint_burden"] == 0
    assert compatibility_summary["retained_public_export_facade_count"] == 4
    assert (
        compatibility_summary["retained_public_export_facades_with_duplicate_exports"]
        == 0
    )
    assert (
        compatibility_summary[
            "retained_public_export_facades_with_resolution_conflicts"
        ]
        == 0
    )
    assert compatibility_summary["twin_pair_count"] == 0
    assert compatibility_summary["removed_compatibility_surfaces_still_present"] == 0
    assert (
        compatibility_summary["removed_compatibility_surfaces_with_src_importers"] == 0
    )
    assert (
        compatibility_summary["removed_compatibility_surfaces_with_test_importers"] == 0
    )

    coverage_summary = coverage["summary"]
    assert coverage_summary["uncovered_module_count"] == 0
    assert coverage_summary["unmeasured_module_count"] == 0
