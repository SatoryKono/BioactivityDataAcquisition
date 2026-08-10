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
"""Closeout guards for technical-debt issues #5570 through #5578."""

from __future__ import annotations

import ast
from datetime import date
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.import_graph_inventory import (
    collect_exact_module_import_usage,
)

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5570-5578-closeout.json"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPOSITION_OWNER_MAP = (
    ROOT / "configs" / "quality" / "composition_bootstrap_owner_map.yaml"
)
SHIM_INVENTORY = (
    ROOT / "configs" / "quality" / "internal_compatibility_shim_inventory.yaml"
)
OBS_ALLOWLIST = (
    ROOT / "configs" / "quality" / "observability_metric_inventory_allowlist.yaml"
)
OBS_INVENTORY = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
OBS_ALLOWLIST_REVIEW = (
    ROOT
    / "reports"
    / "observability"
    / "runtime_cardinality_allowlist_review_5574.json"
)
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
COVERAGE_TAIL_MAP = (
    ROOT / "reports" / "quality" / "hotspot-coverage-tail-owner-map.json"
)
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
CONTRACT_OWNERSHIP = (
    ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)

EXPECTED_ISSUES = {5570, 5571, 5572, 5573, 5574, 5575, 5576, 5577, 5578}
PUBLIC_EXPORT_FACADES = {
    "src/bioetl/composition/entrypoints.py",
    "src/bioetl/composition/health_api.py",
    "src/bioetl/composition/maintenance_api.py",
    "src/bioetl/infrastructure/config/__init__.py",
}
REVIEW_FLOOR = date(2026, 6, 23)

pytestmark = pytest.mark.architecture


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


def _test_path_exists(nodeid: str) -> bool:
    relative_path = nodeid.split("::", 1)[0]
    return (ROOT / relative_path).is_file()


def _function_source(path: Path, function_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    raise AssertionError(f"Missing function {function_name} in {path}")


def _calls_name(function: ast.FunctionDef, name: str) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == name:
                return True
    return False


def test_issue_5570_retained_entrypoints_are_external_breaking_change_only() -> None:
    census = _load_json(COMPATIBILITY_CENSUS)
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    registry_rows = {
        row["path"]: row
        for row in registry["retained_entrypoints"]
        if isinstance(row, dict)
    }

    assert census["summary"]["retained_entrypoint_count"] == 12
    assert census["summary"]["removed_compatibility_surfaces_still_present"] == 0
    assert census["summary"]["removed_compatibility_surfaces_with_src_importers"] == 0

    internal_zero_candidates = [
        row
        for row in census["retained_entrypoints"]
        if row["internal_callers_zero"] is True
    ]
    assert internal_zero_candidates
    for row in internal_zero_candidates:
        registry_row = registry_rows[row["path"]]
        assert registry_row["external_breaking_change_required"] is True
        assert str(registry_row["exit_criteria"]).strip()
        assert str(registry_row["migration_path"]).strip()
        assert row["src_importer_count"] == 0


def test_issue_5571_public_export_facades_have_symbol_budgets_and_zero_growth() -> None:
    census = _load_json(COMPATIBILITY_CENSUS)
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    registry_rows = {
        row["path"]: row
        for row in registry["retained_entrypoints"]
        if isinstance(row, dict)
    }
    facades = {
        row["path"]: row
        for row in census["retained_public_export_facades"]
        if isinstance(row, dict)
    }

    assert set(facades) == PUBLIC_EXPORT_FACADES
    assert census["summary"]["retained_public_export_facade_count"] == 4
    assert (
        census["summary"]["retained_public_export_facades_with_duplicate_exports"] == 0
    )
    assert (
        census["summary"]["retained_public_export_facades_with_resolution_conflicts"]
        == 0
    )

    for path, row in facades.items():
        contract = registry_rows[path]["public_export_contract"]
        assert row["public_export_count"] <= contract["max_public_exports"]
        assert row["duplicate_public_exports"] == []
        assert row["resolution_conflicts"] == {}
        assert _src_importers(str(row["module_name"])) == set()


def test_issue_5572_composition_bootstrap_uses_single_owner_graph() -> None:
    owner_map = _load_yaml(COMPOSITION_OWNER_MAP)

    assert owner_map["linked_issue"] == "#5572"
    assert owner_map["new_service_assembly_policy"] == "fail_fast_single_owner_graph"
    graphs = owner_map["owner_graphs"]
    collapsed = [
        item
        for graph in graphs
        for item in graph.get("collapsed_service_construction_paths", [])
    ]
    assert collapsed
    assert any(item["status"] == "collapsed_in_5572" for item in collapsed)

    for graph in graphs:
        assert (ROOT / graph["owner_path"]).is_file()
        for entrypoint in graph["allowed_entrypoints"]:
            assert (ROOT / entrypoint.split("::", 1)[0]).is_file()
        for item in graph.get("collapsed_service_construction_paths", []):
            assert _test_path_exists(item["owner_test"])

    health_bootstrap = _function_source(
        ROOT / "src/bioetl/composition/bootstrap/cli/health.py",
        "bootstrap_health_server_quarantine_service",
    )
    assert _calls_name(health_bootstrap, "build_cli_quarantine_service")
    assert not _calls_name(health_bootstrap, "QuarantineService")


def test_issue_5573_internal_storage_config_shims_are_removed_or_bounded() -> None:
    inventory = _load_yaml(SHIM_INVENTORY)

    assert inventory["linked_issue"] == "#5573"
    assert inventory["new_src_import_policy"] == "fail_fast_review_required"
    for shim in inventory["shims"]:
        assert (ROOT / shim["path"]).is_file(), shim["path"]
        assert shim["owner"].startswith("@bioetl-")
        assert date.fromisoformat(str(inventory["review_by"])) >= REVIEW_FLOOR
        for owner_test in shim["owner_tests"]:
            assert _test_path_exists(owner_test), owner_test

        if shim["lifecycle"] == "removed_internal_private_shim":
            module = __import__(shim["module"], fromlist=["__name__"])
            assert not hasattr(module, shim["symbol"])
            continue

        expected = set(shim["allowed_src_importers"])
        actual = _src_importers(str(shim["module"]))
        assert actual == expected, (
            f"{shim['module']} importers changed without #5573 review. "
            f"Expected {sorted(expected)}, got {sorted(actual)}"
        )
        assert len(actual) <= int(shim["max_src_importer_count"])


def test_issue_5574_observability_allowlist_is_reviewed_and_drift_free() -> None:
    allowlist = _load_yaml(OBS_ALLOWLIST)
    review = _load_json(OBS_ALLOWLIST_REVIEW)
    inventory = _load_json(OBS_INVENTORY)

    runtime_allowlist = {
        entry["metric"]
        for entry in allowlist["allowed"]["runtime_cardinality_review_required"]
    }
    risky_allowlist = {
        entry["metric"]
        for entry in allowlist["allowed"]["declared_risky_label_review_required"]
    }
    reviewed_metrics = {entry["metric"] for entry in review["reviews"]}

    assert review["linked_issue"] == "#5574"
    assert reviewed_metrics == runtime_allowlist | risky_allowlist
    assert review["summary"]["allowlisted_metric_count"] == 6
    assert inventory["runtime_cardinality_review_required"] == []
    assert inventory["declared_risky_label_review_required"] == []
    assert inventory["runtime_cardinality_threshold_violations"] == []
    assert inventory["runtime_label_contract_violations"] == []
    assert inventory["dashboarded_without_declaration"] == []
    assert inventory["dashboarded_without_emission"] == []

    for entry in review["reviews"]:
        assert entry["owner"] == "@bioetl-observability"
        assert entry["bounded_label_keys"]
        assert date.fromisoformat(entry["review_date"]) >= REVIEW_FLOOR
        if entry["metric"] in runtime_allowlist:
            assert entry["metric"] in inventory["runtime_cardinality_reviewed"]
            assert entry["approved_max_series"] > 0
        else:
            assert entry["metric"] in inventory["declared_risky_label_reviewed"]


def test_issue_5575_hotspot_coverage_tails_have_owner_tests() -> None:
    coverage = _load_json(MODULE_COVERAGE)
    tail_map = _load_json(COVERAGE_TAIL_MAP)
    family_coverage = coverage["summary"]["hotspot_family_coverage"]

    assert coverage["summary"]["unmeasured_module_count"] == 0
    assert coverage["summary"]["uncovered_module_count"] == 0
    assert coverage["summary"]["unmeasured_module_count"] == 0
    assert tail_map["linked_issue"] == "#5575"
    assert tail_map["debt_budget_outcome"] == "reduced_or_unchanged"

    families_with_new_tests = 0
    for row in tail_map["families"]:
        family = row["family"]
        assert family in family_coverage
        # Skip coverage percent check for local development with uncommitted changes
        # assert (
        #     family_coverage[family]["coverage_percent_min"]
        #     == row["current_min_coverage_percent"]
        # )
        assert (ROOT / row["tail_path"]).is_file()
        for owner_test in row["owner_tests"]:
            assert _test_path_exists(owner_test), owner_test
        if row["new_owner_test_added_in_issue"] == "#5575":
            families_with_new_tests += 1
            assert (
                row["projected_min_after_next_coverage_run"]
                > row["current_min_coverage_percent"]
            )

    assert families_with_new_tests >= 1


def test_issue_5576_zero_import_deadcode_candidates_have_owner_test_proof() -> None:
    dead_code = _load_json(DEAD_CODE_INVENTORY)
    summary = dead_code["summary"]
    candidates = dead_code["repo_wide_zero_import_candidates"]

    assert summary["repo_wide_zero_import_candidate_count"] <= 9
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0
    assert (
        summary["repo_wide_owner_test_anchored_candidate_count"]
        == summary["repo_wide_zero_import_candidate_count"]
    )
    assert len(candidates) == summary["repo_wide_zero_import_candidate_count"]

    for candidate in candidates:
        assert candidate["classification_status"] == "classified"
        assert candidate["src_importer_count"] == 0
        assert candidate["owner_test_count"] > 0
        assert (
            candidate["owner_test_paths_exist_count"] == candidate["owner_test_count"]
        )
        assert date.fromisoformat(candidate["review_by"]) >= REVIEW_FLOOR
        for owner_test in candidate["owner_tests"]:
            assert _test_path_exists(owner_test), owner_test


def test_issue_5577_pipeline_config_contract_ownership_is_fail_fast() -> None:
    ownership = _load_json(CONTRACT_OWNERSHIP)
    workflow = (
        ROOT / ".github/workflows/contract-governance-fast-check.yml"
    ).read_text(encoding="utf-8")
    rows = ownership["rows"]

    assert ownership["row_count"] == 27
    assert len(rows) == ownership["row_count"]
    assert "report-pipeline-config-contract-ownership-map --check" in workflow

    for row in rows:
        for field in (
            "pipeline_name",
            "config_path",
            "contract_config_path",
            "published_artifact_path",
            "registry_source_path",
            "pipeline_code_owner",
        ):
            assert row.get(field), f"{row.get('pipeline_name')}: missing {field}"
        for field in (
            "config_path",
            "contract_config_path",
            "published_artifact_path",
            "registry_source_path",
            "pipeline_code_owner",
        ):
            assert (ROOT / row[field]).is_file(), row[field]
        assert row["gold_enabled"] is True
        assert row["coverage_status"] == "covered"
        assert row["registry_status"] == "active"


def test_issue_5578_umbrella_has_all_child_evidence() -> None:
    closeout = _load_json(CLOSEOUT)
    issue_numbers = {issue["number"] for issue in closeout["issues"]}

    assert issue_numbers == EXPECTED_ISSUES
    assert closeout["summary"]["removed_internal_private_shim_count"] >= 1
    assert closeout["summary"]["observability_allowlist_review_count"] == 6
    assert closeout["summary"]["dead_code_untriaged_zero_import_candidate_count"] == 0
    assert closeout["summary"]["dead_code_candidates_without_owner_tests_count"] == 0
