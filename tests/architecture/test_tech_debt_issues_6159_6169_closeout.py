"""Architecture closeout guards for issues #6159, #6160, #6162-#6166, and #6169."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports/quality/tech-debt-issues-6159-6169-closeout.json"
COMPATIBILITY_CENSUS = ROOT / "reports/quality/compatibility-importer-census.json"
MODULE_COVERAGE = ROOT / "reports/quality/module-coverage-inventory.json"
COVERAGE_GATES = ROOT / "configs/quality/module_coverage_gates.yaml"
DEAD_CODE_INVENTORY = ROOT / "reports/quality/dead-code-inventory.json"
CONFIG_DISCREPANCY = ROOT / "reports/quality/config-discrepancy-baseline.json"
CONFIG_BACKLOG = ROOT / "reports/quality/config-surface-backlog.json"
CONTRACT_OWNERSHIP = ROOT / "reports/quality/pipeline-config-contract-ownership-map.json"
DEBT_GATES = ROOT / "reports/quality/debt-governance-gates.json"
SCRIPTS_MANIFEST = ROOT / "configs/quality/scripts_inventory_manifest.json"
SCRIPTS_LIFECYCLE = ROOT / "configs/quality/scripts_lifecycle_registry.json"
DQ_SERVICE = ROOT / "src/bioetl/application/services/data_quality_service.py"
DQ_ANOMALIES = ROOT / "src/bioetl/application/services/data_quality_anomalies.py"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _outcome(issue: str) -> dict[str, Any]:
    payload = _load_json(CLOSEOUT)
    outcomes = payload["outcomes"]
    assert isinstance(outcomes, dict)
    outcome = outcomes[issue]
    assert isinstance(outcome, dict)
    return outcome


def _module_row_by_path(path: str) -> dict[str, Any]:
    inventory = _load_json(MODULE_COVERAGE)
    rows = inventory["modules"]
    assert isinstance(rows, list)
    row = next(
        item
        for item in rows
        if isinstance(item, dict) and item.get("path") == path
    )
    return row


def _script_rows_by_path() -> dict[str, dict[str, Any]]:
    manifest = _load_json(SCRIPTS_MANIFEST)
    rows = manifest["scripts"]
    assert isinstance(rows, list)
    return {
        str(row["path"]): row
        for row in rows
        if isinstance(row, dict) and row.get("path")
    }


def _gate_by_name(name: str) -> dict[str, Any]:
    gates = _load_json(DEBT_GATES)["gates"]
    assert isinstance(gates, list)
    gate = next(
        item
        for item in gates
        if isinstance(item, dict) and item.get("name") == name
    )
    return gate


def test_issues_6159_6169_closeout_scope_is_explicit() -> None:
    payload = _load_json(CLOSEOUT)

    assert payload["schema_version"] == "1.0"
    assert payload["selected_issues"] == [
        6159,
        6160,
        6162,
        6163,
        6164,
        6165,
        6166,
        6169,
    ]
    assert set(payload["outcomes"]) == {
        "6160",
        "6162",
        "6163",
        "6164",
        "6165",
        "6166",
        "6169",
    }
    assert payload["umbrella_issue"] == {
        "issue": 6159,
        "selected_scope_complete": True,
        "full_umbrella_blockers_outside_selected_scope": [6161, 6167, 6168],
    }

    for evidence_path in _outcome("6160")["evidence"]:
        assert (ROOT / evidence_path).exists(), evidence_path


def test_issue_6162_compatibility_facades_are_frozen_without_drift() -> None:
    outcome = _outcome("6162")
    summary = _load_json(COMPATIBILITY_CENSUS)["summary"]

    assert summary["retained_entrypoint_count"] == outcome["retained_entrypoint_count"]
    assert (
        summary["retained_public_export_facade_count"]
        == outcome["retained_public_export_facade_count"]
    )
    assert summary["retained_public_entrypoint_burden"] == 0
    assert summary["removed_compatibility_surfaces_with_src_importers"] == 0
    assert summary["removed_compatibility_surfaces_still_present"] == 0
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0
    assert summary["retained_public_export_facades_with_wrapper_contract_drift"] == 0


def test_issue_6163_data_quality_service_hotspot_is_reduced() -> None:
    outcome = _outcome("6163")
    service_source = DQ_SERVICE.read_text(encoding="utf-8")
    helper_source = DQ_ANOMALIES.read_text(encoding="utf-8")
    service_lines = len(service_source.splitlines())

    assert service_lines < outcome["line_count_before"]
    assert service_lines <= outcome["line_count_after_max"]
    assert "_emit_validation_gauges(" in service_source
    assert "bioetl_dq_validation_score" not in service_source
    assert "def _emit_validation_gauges(" in helper_source
    assert "bioetl_dq_validation_score" in helper_source

    row = _module_row_by_path(outcome["reduced_surface"])
    assert row["source_lines"] == service_lines
    assert row["coverage_percent"] == 100.0
    assert row["missing_lines"] == 0


def test_issue_6164_replay_sensitive_coverage_floors_are_100_percent() -> None:
    outcome = _outcome("6164")
    policy = _load_yaml(COVERAGE_GATES)["replay_sensitive_coverage_floors"]
    assert isinstance(policy, dict)
    assert policy["mode"] == "fail-fast"

    modules = policy["modules"]
    assert isinstance(modules, list) and modules
    for entry in modules:
        assert isinstance(entry, dict)
        assert entry["min_coverage_percent"] == outcome["replay_sensitive_floor_percent"]
        row = _module_row_by_path(str(entry["path"]))
        assert row["coverage_percent"] >= entry["min_coverage_percent"]
        assert row["missing_lines"] == 0
        for owner_test in entry["owner_tests"]:
            assert (ROOT / str(owner_test)).exists()


def test_issue_6165_dead_code_zero_import_candidates_are_triaged() -> None:
    outcome = _outcome("6165")
    inventory = _load_json(DEAD_CODE_INVENTORY)
    summary = inventory["summary"]

    assert summary["repo_wide_zero_import_candidate_count"] == (
        outcome["repo_wide_zero_import_candidate_count"]
    )
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == (
        outcome["repo_wide_untriaged_zero_import_candidate_count"]
    )
    assert summary["repo_wide_owner_test_anchored_candidate_count"] == (
        outcome["repo_wide_owner_test_anchored_candidate_count"]
    )
    for row in inventory["repo_wide_zero_import_candidates"]:
        assert row["classification_status"] == "classified"
        assert row["owner_test_count"] == row["owner_test_paths_exist_count"]
        assert row["owner_test_count"] >= 1


def test_issue_6166_config_contract_drift_is_zero() -> None:
    outcome = _outcome("6166")
    config_metrics = _load_json(CONFIG_DISCREPANCY)["metrics"]
    config_backlog = _load_json(CONFIG_BACKLOG)
    ownership = _load_json(CONTRACT_OWNERSHIP)

    assert _gate_by_name("contract_registry_blocking_drift")["status"] == "pass"
    assert _gate_by_name("dq_contract_registry_blocking_drift")["status"] == "pass"
    assert (
        _gate_by_name("config_discrepancy_inconsistent_parameters")["status"]
        == "pass"
    )
    assert (
        _gate_by_name("config_discrepancy_raw_inconsistent_parameters")["status"]
        == "pass"
    )
    assert config_metrics["inconsistent_parameter_count"] == (
        outcome["config_inconsistent_parameter_count"]
    )
    assert config_metrics["raw_inconsistent_parameter_count"] == (
        outcome["config_raw_inconsistent_parameter_count"]
    )
    assert config_metrics["sanctioned_partial_parameter_count"] == (
        outcome["config_sanctioned_partial_parameter_count"]
    )
    assert config_backlog["entity_effective"]["inconsistent_parameter_count"] == 0
    assert config_backlog["entity_effective"]["raw_inconsistent_parameter_count"] == 0
    assert ownership["row_count"] == len(ownership["rows"])
    assert {row["coverage_status"] for row in ownership["rows"]} == {"covered"}


def test_issue_6169_script_governance_ratchet_has_headroom() -> None:
    outcome = _outcome("6169")
    manifest = _load_json(SCRIPTS_MANIFEST)
    summary = manifest["summary"]
    status_counts = summary["status_counts"]
    rows_by_path = _script_rows_by_path()
    lifecycle_entries = _load_json(SCRIPTS_LIFECYCLE)["entries"]

    assert status_counts["active"] == outcome["active_script_count"]
    assert status_counts["active"] <= outcome["active_script_count_max"]
    assert status_counts.get("unknown", 0) == 0
    assert status_counts.get("orphan", 0) == 0
    assert status_counts.get("legacy", 0) == 0
    assert sum(
        1
        for row in rows_by_path.values()
        if row["status"] == "supporting" and row["reference_count"] == 0
    ) == outcome["zero_reference_supporting_script_count"]

    for script_path in outcome["newly_governed_supporting_scripts"]:
        row = rows_by_path[script_path]
        lifecycle = lifecycle_entries[script_path]
        assert row["status"] == "supporting"
        assert row["lifecycle_decision"] in {
            "compatibility_wrapper",
            "legacy_manual_utility",
        }
        assert lifecycle["decision"] == row["lifecycle_decision"]
        assert lifecycle["review_by"] == "2026-09-30"
