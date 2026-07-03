"""Closeout guards for technical-debt issues #5648 through #5654."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.ci.validate_registry_dq_refs import build_diagnostics_payload

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5648-5654-closeout.json"
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
HOTSPOT_BASELINE = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
ARCHITECTURE_SCORECARD = (
    ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
)
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
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
CONTRACT_DIAGNOSTICS = (
    ROOT / "reports" / "quality" / "contract-registry-diagnostics.json"
)

EXPECTED_ISSUES = {5648, 5649, 5650, 5651, 5652, 5653, 5654}
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


def _family(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for family in payload["families"]:
        if family["name"] == name:
            return family
    raise AssertionError(f"missing hotspot family: {name}")


def _scorecard_family(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for family in payload["hotspot_family_ratchets"]["families"]:
        if family["name"] == name:
            return family
    raise AssertionError(f"missing scorecard family: {name}")


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


def test_closeout_artifact_covers_requested_issue_chain() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["schema_version"] == "tech-debt-issues-5648-5654-closeout-v1"
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert {issue["number"] for issue in closeout["issues"]} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in closeout["issues"])

    for issue in closeout["issues"]:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issues_5648_5649_5650_duplication_is_below_opening_baselines() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)

    cli = _target(duplication, "src/bioetl/interfaces/cli")
    adapters = _target(duplication, "src/bioetl/infrastructure/adapters")
    pipelines = _target(duplication, "src/bioetl/application/pipelines")
    bootstrap = _target(duplication, "src/bioetl/composition/bootstrap")

    assert duplication["summary"]["total_duplicate_clusters"] <= 75
    assert cli["duplicate_count"] == 0
    assert cli["duplicate_count"] < 3
    assert adapters["duplicate_count"] <= 56
    assert adapters["duplicate_count"] < 67
    assert pipelines["duplicate_count"] <= 13
    assert pipelines["duplicate_count"] < 18
    assert bootstrap["duplicate_count"] == 0


def test_issue_5650_contract_and_dq_diagnostics_remain_clean() -> None:
    gates = _load_json(DEBT_GATES)
    contract = _load_json(CONTRACT_DIAGNOSTICS)
    dq = build_diagnostics_payload(ROOT)

    assert _gate(gates, "contract_registry_blocking_drift")["status"] == "pass"
    assert _gate(gates, "dq_contract_registry_blocking_drift")["status"] == "pass"
    assert contract["valid"] is True
    assert contract["blocking_issue_count"] == 0
    assert dq["valid"] is True
    assert dq["blocking_issue_count"] == 0


def test_issue_5651_public_compatibility_surfaces_are_fully_justified() -> None:
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]
    public_facades = [
        entry
        for entry in census["retained_entrypoints"]
        if "public_export_count" in entry
    ]

    assert registry["transition_debt"] == []
    assert summary["retained_entrypoint_count"] == 12
    assert summary["retained_public_entrypoint_burden"] == 0
    assert summary["twin_pair_count"] == 0
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

    for entry in census["retained_entrypoints"]:
        assert entry["src_importer_count"] == 0

    for facade in public_facades:
        assert facade["public_export_count"] <= facade["max_public_exports"]
        assert facade["duplicate_public_exports"] == []
        assert facade["duplicate_lazy_export_keys"] == []
        assert facade["resolution_conflicts"] == {}


def test_issue_5652_silver_filter_identity_facade_has_zero_src_importers() -> None:
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


def test_issue_5653_dead_code_review_window_is_fully_triaged() -> None:
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


def test_issue_5654_hotspot_warnings_are_reduced_without_budget_growth() -> None:
    baseline = _load_json(HOTSPOT_BASELINE)
    gates = _load_json(DEBT_GATES)
    scorecard = _load_yaml(DEBT_SCORECARD)
    architecture = _load_json(ARCHITECTURE_SCORECARD)

    baseline_family = _family(baseline, "composition_factories_pipeline")
    scorecard_family = _scorecard_family(scorecard, "composition_factories_pipeline")
    hotspot_gate = _gate(gates, "hotspot_family_baseline_budget_warnings")

    assert baseline["summary"]["budget_warnings"] == 0
    assert baseline["summary"]["budget_review_notes"] == sum(
        len(family["budget_review_notes"]) for family in baseline["families"]
    )
    assert baseline["summary"]["budget_review_notes"] <= 6
    assert baseline_family["files_ge_250_loc"] == 2
    assert baseline_family["bounded_growth_budgets"]["files_ge_250_loc"] == 3
    assert baseline_family["budget_warnings"] == []
    assert baseline_family["budget_review_notes"] == [
        "at_budget:max_internal_fan_in=3/3"
    ]
    assert scorecard_family["metrics"]["files_ge_250_loc"] == 2
    assert scorecard_family["bounded_growth_budgets"]["files_ge_250_loc"] == 3
    assert _gate(gates, "debt_scorecard_budget_violations")["status"] == "pass"
    assert _gate(gates, "debt_budget_growth_policy")["status"] == "pass"
    assert hotspot_gate["status"] == "pass"
    assert hotspot_gate["current"] == 0
    assert (
        architecture["source_artifacts"]["hotspot_family_baseline"]["budget_warnings"]
        == 0
    )
    assert architecture["integral_score"] >= 8.31
