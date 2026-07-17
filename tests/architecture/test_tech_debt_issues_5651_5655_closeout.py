"""Closeout guards for Stream B technical-debt issues #5651, #5652, #5653, #5655."""

from __future__ import annotations

import ast
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.ci.validate_registry_dq_refs import build_diagnostics_payload

pytestmark = pytest.mark.architecture
REFERENCE_TODAY = date(2026, 7, 6)

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5651-5655-closeout.json"
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
INTERNAL_SHIMS = (
    ROOT / "configs" / "quality" / "internal_compatibility_shim_inventory.yaml"
)
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
CONTRACT_DIAGNOSTICS = (
    ROOT / "reports" / "quality" / "contract-registry-diagnostics.json"
)
CONFIG_DISCREPANCY = ROOT / "reports" / "quality" / "config-discrepancy-baseline.json"
RUNTIME_CARDINALITY_REVIEW = (
    ROOT / "reports" / "observability" / "runtime_cardinality_review.json"
)
RUNTIME_CARDINALITY_INVENTORY = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
BRONZE_FIXTURE_GAPS = ROOT / "configs" / "base" / "bronze_fixture_gaps.yaml"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
CONTRACT_WORKFLOW = (
    ROOT / ".github" / "workflows" / "contract-governance-fast-check.yml"
)
EXPECTED_ISSUES = {5651, 5652, 5653, 5655}
PUBLIC_EXPORT_FACADE_PATHS = {
    "src/bioetl/composition/entrypoints.py",
    "src/bioetl/composition/health_api.py",
    "src/bioetl/composition/maintenance_api.py",
    "src/bioetl/infrastructure/config/__init__.py",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _gate(gates: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [gate for gate in gates["gates"] if gate["name"] == name]
    assert len(matches) == 1, name
    return matches[0]


def _src_importers(module_name: str) -> set[str]:
    importers: set[str] = set()
    for path in (ROOT / "src").rglob("*.py"):
        repo_path = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == module_name for alias in node.names):
                    importers.add(repo_path)
            elif isinstance(node, ast.ImportFrom) and node.module == module_name:
                importers.add(repo_path)
    return importers


def test_stream_b_closeout_artifact_is_complete_and_budget_safe() -> None:
    closeout = _load_json(CLOSEOUT)

    assert set(closeout["issues"]) == EXPECTED_ISSUES
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert set(closeout["outcomes"]) == {str(issue) for issue in EXPECTED_ISSUES}
    assert all(
        outcome["status"] == "closeable" for outcome in closeout["outcomes"].values()
    )
    assert closeout["outcomes"]["5652"]["outcome"] == "improved"


def test_issue_5655_freshness_gates_are_fail_fast_and_clean() -> None:
    gates = _load_json(DEBT_GATES)
    contract = _load_json(CONTRACT_DIAGNOSTICS)
    dq = build_diagnostics_payload(ROOT)
    config = _load_json(CONFIG_DISCREPANCY)
    review = _load_json(RUNTIME_CARDINALITY_REVIEW)
    inventory = _load_json(RUNTIME_CARDINALITY_INVENTORY)
    bronze_gaps = _load_yaml(BRONZE_FIXTURE_GAPS)
    workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
    contract_workflow = CONTRACT_WORKFLOW.read_text(encoding="utf-8")

    for gate_name in (
        "contract_registry_blocking_drift",
        "dq_contract_registry_blocking_drift",
        "config_discrepancy_inconsistent_parameters",
        "config_discrepancy_raw_inconsistent_parameters",
        "observability_runtime_cardinality_review_required",
        "observability_runtime_cardinality_threshold_violations",
        "observability_release_review_status",
        "observability_release_review_freshness",
        "observability_touched_metric_inventory_freshness",
        "observability_touched_metric_review_freshness",
    ):
        assert _gate(gates, gate_name)["status"] == "pass"

    assert contract["valid"] is True
    assert contract["blocking_issue_count"] == 0
    assert dq["valid"] is True
    assert dq["blocking_issue_count"] == 0
    assert (
        _gate(gates, "dq_contract_registry_blocking_drift")["source_artifact"]
        == "scripts/engineering/ci/validate_registry_dq_refs.py::build_diagnostics_payload"
    )
    assert config["metrics"]["inconsistent_parameter_count"] == 0
    assert config["metrics"]["raw_inconsistent_parameter_count"] == 0
    assert review["status"] == "passed"
    assert inventory["runtime_cardinality_review_required"] == []
    assert inventory["runtime_cardinality_threshold_violations"] == []
    assert inventory["unused_declared_observability_events"] == []
    assert inventory["unused_declared_metrics"] == []
    assert bronze_gaps["gaps"] == {}
    assert "report-debt-governance-gates --check --changed-from-ref" in workflow
    assert "report-observability-metric-inventory" in workflow
    assert "validate_contract_registry.py" in contract_workflow
    assert "validate_registry_dq_refs.py" in contract_workflow


def test_issue_5651_retained_public_compatibility_surfaces_are_justified() -> None:
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]
    retained = census["retained_entrypoints"]
    public_facades = [entry for entry in retained if "public_export_count" in entry]

    assert registry["transition_debt"] == []
    assert summary["retained_entrypoint_count"] == 12
    assert summary["retained_public_entrypoint_burden"] == 0
    assert summary["retained_public_export_facade_count"] == 4
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0
    assert {facade["path"] for facade in public_facades} == PUBLIC_EXPORT_FACADE_PATHS

    for entry in registry["retained_entrypoints"]:
        assert entry["status"] == "public-entrypoint"
        assert entry["external_breaking_change_required"] is True
        assert entry["review_date"]
        assert entry["migration_path"]
        assert entry["exit_criteria"]

    for entry in retained:
        assert entry["src_importer_count"] == 0

    for facade in public_facades:
        assert facade["public_export_count"] <= facade["max_public_exports"]
        assert facade["duplicate_public_exports"] == []
        assert facade["duplicate_lazy_export_keys"] == []
        assert facade["orphan_lazy_export_keys"] == []
        assert facade["orphan_dunder_getattr_exports"] == []
        assert facade["resolution_conflicts"] == {}


def test_issue_5652_stream_b_silver_filter_identity_facade_has_zero_src_importers() -> (
    None
):
    shims = _load_yaml(INTERNAL_SHIMS)["shims"]
    row = next(
        shim
        for shim in shims
        if shim["id"] == "silver-filter-migration-runtime-identity"
    )
    actual = _src_importers("bioetl.infrastructure.config.silver_filter_migration")

    assert row["lifecycle"] == "retained_external_identity_facade"
    assert row["canonical_target"] == "bioetl.domain.filtering.silver_filter_identity"
    assert row["max_src_importer_count"] == 0
    assert row["allowed_src_importers"] == []
    assert actual == set()


def test_issue_5653_dead_code_review_window_is_current_and_fully_triaged() -> None:
    inventory = _load_json(DEAD_CODE_INVENTORY)
    review = inventory["review_window"]
    summary = inventory["summary"]
    next_review_by = date.fromisoformat(review["next_review_by"])

    assert review["mode"] == "fail-fast-zero-untriaged"
    assert review["max_untriaged_zero_import_candidates"] == 0
    assert review["snapshot_matches_last_reviewed"] is True
    assert next_review_by >= REFERENCE_TODAY
    assert summary["repo_wide_zero_import_candidate_count"] == len(
        inventory["repo_wide_zero_import_candidates"]
    )
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
