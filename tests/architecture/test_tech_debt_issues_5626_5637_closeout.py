"""Closeout guards for technical-debt issues #5626 through #5637."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.ci.validate_registry_dq_refs import build_diagnostics_payload
from scripts.engineering.qa.import_graph_inventory import (
    collect_exact_module_import_usage,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5626-5637-closeout.json"
INTERNAL_SHIMS = (
    ROOT / "configs" / "quality" / "internal_compatibility_shim_inventory.yaml"
)
RUNTIME_CARDINALITY_REVIEW = (
    ROOT / "reports" / "observability" / "runtime_cardinality_review.json"
)
RUNTIME_CARDINALITY_INVENTORY = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
OBSERVABILITY_GOVERNANCE = (
    ROOT / "configs" / "quality" / "observability_metric_governance.yaml"
)
CONTRACT_DIAGNOSTICS = (
    ROOT / "reports" / "quality" / "contract-registry-diagnostics.json"
)
ARCHITECTURE_SCORECARD = (
    ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
)
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
TEST_GOVERNANCE_CONFIG = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
TEST_GOVERNANCE_REPORT = ROOT / "reports" / "quality" / "test-governance-current.json"
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
HOTSPOT_BASELINE = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"

EXPECTED_ISSUES = {
    5626,
    5627,
    5628,
    5629,
    5630,
    5631,
    5632,
    5633,
    5634,
    5635,
    5636,
    5637,
}
PUBLIC_EXPORT_FACADES = {
    "src/bioetl/composition/entrypoints.py",
    "src/bioetl/composition/health_api.py",
    "src/bioetl/composition/maintenance_api.py",
    "src/bioetl/infrastructure/config/__init__.py",
}
SILVER_FILTER_IDENTITY_IMPORTERS = {
    "src/bioetl/composition/bootstrap/runtime/assembly.py",
    "src/bioetl/composition/factories/pipeline/checkpoint_metadata_helpers.py",
    "src/bioetl/composition/runtime_builders/_effective_config_artifact_builder_support.py",
    "src/bioetl/composition/runtime_builders/_inputs_resolution_support.py",
    "src/bioetl/composition/runtime_builders/_run_manifest_creation_support_helpers.py",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _src_importers(module_name: str) -> set[str]:
    usage = collect_exact_module_import_usage(ROOT, module_name)
    return {str(path) for path in usage["src"]}


def _test_importers(module_name: str) -> set[str]:
    usage = collect_exact_module_import_usage(ROOT, module_name)
    return {str(path) for path in usage["tests"]}


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt governance gate: {name}")


def test_closeout_artifact_covers_requested_issues__5626_5637() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5626-5637-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5627_silver_metadata_request_reexport_shim_is_retired() -> None:
    shims = _load_yaml(INTERNAL_SHIMS)["shims"]
    shim_ids = {shim["id"] for shim in shims}
    shim_path = (
        ROOT / "src/bioetl/infrastructure/storage/silver/metadata_request_models.py"
    )

    assert "silver-metadata-request-models-reexport" not in shim_ids
    assert not shim_path.exists()
    assert (
        _src_importers("bioetl.infrastructure.storage.silver.metadata_request_models")
        == set()
    )
    assert (
        _test_importers("bioetl.infrastructure.storage.silver.metadata_request_models")
        == set()
    )


def test_issue_5628_runtime_cardinality_evidence_is_release_grade() -> None:
    review = _load_json(RUNTIME_CARDINALITY_REVIEW)
    inventory = _load_json(RUNTIME_CARDINALITY_INVENTORY)
    governance = _load_yaml(OBSERVABILITY_GOVERNANCE)
    gates = _load_json(DEBT_GATES)
    generated_at = datetime.fromisoformat(review["generated_at"].replace("Z", "+00:00"))

    assert (datetime.now(UTC) - generated_at).days <= 1
    assert review["status"] == "passed"
    assert review["mode"] == "live_review"
    assert review["degraded_reasons"] == []
    assert review["local_cardinality_fallback_allowed"] is False
    assert "--fail-on-degraded-live-review" in review["source_command"]
    assert review["live_threshold_violations"] == []
    assert inventory["runtime_cardinality_review_required"] == []
    assert inventory["runtime_cardinality_threshold_violations"] == []

    runtime_review = governance["runtime_cardinality_review"]
    assert runtime_review["live_evidence"]["fail_on_degraded_release_review"] is True
    assert runtime_review["local_fallback_evidence"]["release_gate_allowed"] is False
    assert _gate(gates, "observability_release_review_status")["status"] == "pass"
    assert _gate(gates, "observability_release_review_freshness")["status"] == "pass"


def test_issue_5629_cli_command_shell_duplication_is_below_opening_baseline() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}

    assert by_target["src/bioetl/interfaces/cli"]["duplicate_count"] == 3
    assert by_target["src/bioetl/interfaces/cli"]["duplicate_count"] < 6


def test_issue_5630_adapter_layer_duplication_is_below_opening_baseline() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}

    assert by_target["src/bioetl/infrastructure/adapters"]["duplicate_count"] == 67
    assert by_target["src/bioetl/infrastructure/adapters"]["duplicate_count"] < 72


def test_issue_5631_pipeline_transformer_duplication_is_below_opening_baseline() -> (
    None
):
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}

    assert by_target["src/bioetl/application/pipelines"]["duplicate_count"] == 18
    assert by_target["src/bioetl/application/pipelines"]["duplicate_count"] < 22


def test_issue_5632_hotspot_warning_count_and_budget_are_ratcheted_down() -> None:
    baseline = _load_json(HOTSPOT_BASELINE)
    scorecard = _load_yaml(DEBT_SCORECARD)
    baseline_families = {family["name"]: family for family in baseline["families"]}
    scorecard_families = {
        family["name"]: family
        for family in scorecard["hotspot_family_ratchets"]["families"]
    }
    baseline_family = baseline_families["composition_bootstrap_runtime"]
    scorecard_family = scorecard_families["composition_bootstrap_runtime"]

    assert baseline["summary"]["budget_warnings"] == 8
    assert baseline["summary"]["budget_warnings"] < 9
    assert baseline_family["files_ge_250_loc"] == 0
    assert baseline_family["bounded_growth_budgets"]["files_ge_250_loc"] == 0
    assert scorecard_family["bounded_growth_budgets"]["files_ge_250_loc"] == 0


def test_issue_5633_contract_and_dq_diagnostics_are_blocker_free() -> None:
    contract = _load_json(CONTRACT_DIAGNOSTICS)
    dq = build_diagnostics_payload(ROOT)
    scorecard = _load_json(ARCHITECTURE_SCORECARD)
    gates = _load_json(DEBT_GATES)

    assert contract["valid"] is True
    assert contract["blocking_issue_count"] == 0
    assert dq["valid"] is True
    assert dq["checked_entries_count"] == contract["entries_count"]
    assert dq["blocking_issue_count"] == 0
    assert dq["issue_count"] == 0
    assert scorecard["metrics"]["contract_blocking_issue_count"] == 0
    assert scorecard["metrics"]["dq_blocking_issue_count"] == 0
    assert _gate(gates, "contract_registry_blocking_drift")["status"] == "pass"
    assert _gate(gates, "dq_contract_registry_blocking_drift")["status"] == "pass"


def test_issue_5634_retained_compatibility_test_inventory_is_reviewed() -> None:
    config = _load_yaml(TEST_GOVERNANCE_CONFIG)
    report_payload = _load_json(TEST_GOVERNANCE_REPORT)
    report = report_payload["report"]
    inventory = config["compatibility_test_inventory"]

    assert config["budgets"]["compatibility_test_file_max"] == 25
    assert inventory["total_files"] == 25
    assert report["compatibility_test_files"] == 25
    assert report_payload["budget_violations"] == []
    assert date.fromisoformat(str(inventory["default_review_date"])) >= date(
        2026, 9, 30
    )
    assert {entry["path"] for entry in inventory["entries"]} == set(
        report["compatibility_files"]
    )
    for entry in inventory["entries"]:
        assert (ROOT / entry["path"]).is_file(), entry["path"]
        assert entry["decision"].startswith("retained_")
        assert date.fromisoformat(str(entry["review_date"])) >= date(2026, 9, 30)


def test_issue_5635_dead_code_inventory_review_window_is_current() -> None:
    inventory = _load_json(DEAD_CODE_INVENTORY)
    summary = inventory["summary"]
    review_window = inventory["review_window"]

    assert review_window["mode"] == "fail-fast-zero-untriaged"
    assert review_window["max_untriaged_zero_import_candidates"] == 0
    assert date.fromisoformat(review_window["next_review_by"]) >= date(2026, 9, 14)
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0
    for row in inventory["repo_wide_zero_import_candidates"]:
        assert row["classification_status"] == "classified"
        assert row["owner_test_count"] == row["owner_test_paths_exist_count"]
        assert row["owner_test_count"] >= 1


def test_issue_5636_public_lazy_export_facades_are_bounded_and_drift_free() -> None:
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]
    public_facades = census["retained_public_export_facades"]

    assert summary["retained_public_export_facade_count"] == 4
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0
    assert {facade["path"] for facade in public_facades} == PUBLIC_EXPORT_FACADES

    registry_by_path = {
        entry["path"]: entry for entry in registry["retained_entrypoints"]
    }
    for facade in public_facades:
        assert facade["duplicate_public_exports"] == []
        assert facade["duplicate_lazy_export_keys"] == []
        assert facade["orphan_lazy_export_keys"] == []
        assert facade["orphan_dunder_getattr_exports"] == []
        assert facade["resolution_conflicts"] == {}
        assert facade["public_export_count"] <= facade["max_public_exports"]
        assert registry_by_path[facade["path"]]["public_export_contract"]


def test_issue_5637_silver_filter_identity_adapter_budget_is_ratcheted() -> None:
    shims = _load_yaml(INTERNAL_SHIMS)["shims"]
    row = next(
        shim
        for shim in shims
        if shim["id"] == "silver-filter-migration-runtime-identity"
    )
    actual = _src_importers("bioetl.infrastructure.config.silver_filter_migration")

    assert row["max_src_importer_count"] == 5
    assert set(row["allowed_src_importers"]) == SILVER_FILTER_IDENTITY_IMPORTERS
    assert actual == SILVER_FILTER_IDENTITY_IMPORTERS
    assert len(actual) <= row["max_src_importer_count"]
    assert "src/bioetl/infrastructure/config/filter_config_loader.py" not in actual
    assert "src/bioetl/infrastructure/schemas/filter_config.py" not in actual
    assert "src/bioetl/infrastructure/schemas/pipeline_config.py" not in actual
    assert (
        "src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py"
        not in actual
    )
