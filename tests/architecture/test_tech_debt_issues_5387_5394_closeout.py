"""Closeout guardrails for technical-debt issues #5387-#5394."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5387-5394-closeout.json"
SCORECARD = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
COMPAT_CENSUS = ROOT / "reports" / "quality" / "compatibility-importer-census.json"
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
VCR_CATALOG = ROOT / "reports" / "quality" / "vcr-metadata-catalog.json"
CONFIG_BASELINE = ROOT / "reports" / "quality" / "config-discrepancy-baseline.json"
CONFIG_TAXONOMY_REVIEW = (
    ROOT / "reports" / "quality" / "config-compatibility-legacy-taxonomy-review.json"
)
FULL_APP_DUPLICATION = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
CONTROL_PLANE_DUPLICATION = (
    ROOT / "reports" / "quality" / "control-plane-duplication.json"
)
HOTSPOT_FAMILIES = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
SEMANTIC_USE_CASE_AUDIT = (
    ROOT / "reports" / "quality" / "semantic-ddd-use-case-audit-2026-06-17.md"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _closeout_by_issue() -> dict[int, dict[str, Any]]:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]
    assert isinstance(issues, list)
    return {int(issue["number"]): issue for issue in issues if isinstance(issue, dict)}


def test_closeout_artifact_covers_all_requested_issues() -> None:
    payload = _load_json(CLOSEOUT)
    issues = _closeout_by_issue()

    assert payload["schema_version"] == "tech-debt-issues-5387-5394-closeout-v1"
    assert set(issues) == {5387, 5388, 5389, 5390, 5391, 5392, 5393, 5394}
    assert payload["debt_budget_outcome"] == "unchanged_or_improved"
    assert all(issue["status"] for issue in issues.values())


def test_issue_5387_scorecard_coverage_evidence_matches_inventory() -> None:
    scorecard = _load_json(SCORECARD)
    inventory = _load_json(MODULE_COVERAGE)
    summary = inventory["summary"]

    source_artifact = scorecard["source_artifacts"]["module_coverage_inventory"]
    assert source_artifact["coverage_xml_sha256"] == inventory["coverage_xml_sha256"]
    assert source_artifact["source_tree_sha256"] == inventory["source_tree_sha256"]
    assert scorecard["metrics"]["source_module_count"] == summary["source_module_count"]
    assert (
        scorecard["metrics"]["unmeasured_module_count"]
        == summary["unmeasured_module_count"]
    )
    assert (
        scorecard["metrics"]["uncovered_module_count"]
        == summary["uncovered_module_count"]
    )


def test_issue_5388_compatibility_facade_counts_stay_within_ratchets() -> None:
    census = _load_json(COMPAT_CENSUS)
    debt_scorecard = _load_yaml(DEBT_SCORECARD)
    metrics = debt_scorecard["compatibility_debt_metrics"]["metrics"]
    summary = census["summary"]

    assert summary["retained_entrypoint_count"] <= metrics[
        "retained_public_entrypoint_burden"
    ]["max_count"]
    assert summary["retained_public_export_facade_count"] <= metrics[
        "retained_public_export_facade_burden"
    ]["max_count"]
    assert summary["removed_compatibility_surfaces_with_src_importers"] == 0
    assert summary["removed_compatibility_surfaces_still_present"] == 0
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0


def test_issue_5389_control_plane_use_case_seams_remain_explicit() -> None:
    control_plane_root = ROOT / "src" / "bioetl" / "application" / "services" / "control_plane"
    for package in ("manifest", "ledger", "replay", "effective_config", "workflow"):
        assert (control_plane_root / package / "__init__.py").exists(), package

    duplication = _load_json(CONTROL_PLANE_DUPLICATION)
    assert duplication["summary"]["total_duplicate_clusters"] == 0
    assert duplication["summary"]["total_raw_duplicate_clusters"] == 0

    hotspot = _load_json(HOTSPOT_FAMILIES)
    family = next(
        row
        for row in hotspot["families"]
        if row["name"] == "application_services_control_plane"
    )
    assert family["budget_warnings"] == []

    audit_text = SEMANTIC_USE_CASE_AUDIT.read_text(encoding="utf-8")
    assert "Use-case ownership remains in Application" in audit_text


def test_issue_5390_vcr_metadata_review_debt_is_zero() -> None:
    catalog = _load_json(VCR_CATALOG)
    totals = catalog["totals"]

    assert totals["metadata_review_required_cassette_count"] == 0
    assert totals["unowned_cassette_count"] == 0
    assert totals["duplicate_scenario_stem_count"] == 0


def test_issue_5391_config_compatibility_legacy_taxonomy_is_no_growth() -> None:
    baseline = _load_json(CONFIG_BASELINE)
    review = _load_json(CONFIG_TAXONOMY_REVIEW)
    debt_scorecard = _load_yaml(DEBT_SCORECARD)
    taxonomy_policy = debt_scorecard["config_surface_ratchet"]["parameter_taxonomy"][
        "groups"
    ]

    assert baseline["metrics"]["inconsistent_parameter_count"] == 0
    assert baseline["metrics"]["raw_inconsistent_parameter_count"] == 0

    for family_name, family_review in review["families"].items():
        group_count = baseline["parameter_taxonomy"]["families"][family_name][
            "groups"
        ].get("compatibility_legacy", 0)
        legacy_policy = taxonomy_policy[family_name]["compatibility_legacy"]

        assert family_review["compatibility_legacy_count"] == group_count
        assert legacy_policy["current_count"] == group_count
        assert legacy_policy["max_count"] == group_count
        assert legacy_policy["target_count"] == 0
        assert family_review["review_date"] == "2026-09-30"


def test_issue_5392_coverage_tail_reduction_matches_live_inventory() -> None:
    closeout = _closeout_by_issue()[5392]
    inventory = _load_json(MODULE_COVERAGE)
    rows = inventory["modules"]
    below_85 = [
        row
        for row in rows
        if row["coverage_percent"] is not None and row["coverage_percent"] < 85
    ]
    by_path = {row["path"]: row for row in rows}
    delta = closeout["coverage_tail_delta"]
    improved_path = delta["improved_module"]
    improved_row = by_path[improved_path]

    assert len(below_85) == delta["after_below_85_module_count"]
    assert (
        delta["after_below_85_module_count"]
        - delta["before_below_85_module_count"]
        == delta["below_85_module_count_delta"]
    )
    assert delta["below_85_module_count_delta"] < 0
    assert improved_row["coverage_percent"] == delta["after_coverage_percent"]
    assert improved_row["coverage_percent"] >= 85
    assert inventory["summary"]["uncovered_module_count"] == 0


def test_issue_5393_full_app_duplication_baseline_covers_required_scope() -> None:
    payload = _load_json(FULL_APP_DUPLICATION)
    expected_targets = {
        "src/bioetl/infrastructure/adapters",
        "src/bioetl/application/pipelines",
        "src/bioetl/composition/bootstrap",
        "src/bioetl/interfaces/cli",
    }
    rows = payload["targets"]

    assert payload["summary"]["targets"] == len(expected_targets)
    assert {row["target"] for row in rows} == expected_targets
    assert payload["summary"]["total_duplicate_clusters"] == sum(
        int(row["duplicate_count"]) for row in rows
    )


def test_issue_5394_legacy_checkpoint_hydration_is_confined_to_load_seam() -> None:
    allowed_source_callers = {
        "src/bioetl/application/core/lifecycle/checkpoint_load_validation.py",
    }
    callers: set[str] = set()
    for path in (ROOT / "src" / "bioetl").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "from_legacy_metadata":
                    callers.add(path.relative_to(ROOT).as_posix())

    assert callers == allowed_source_callers

    manifest_validation = (
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "control_plane"
        / "manifest"
        / "validation.py"
    ).read_text(encoding="utf-8")
    assert "resolved_config_hash as a canonical config " in manifest_validation
    assert "identity anchor; legacy config_hash is compatibility-only" in manifest_validation
    assert "effective_config_hash as the replay identity " in manifest_validation
    assert "config anchor; legacy config_hash is compatibility-only" in manifest_validation
    assert "legacy config_hash is compatibility-only" in manifest_validation
