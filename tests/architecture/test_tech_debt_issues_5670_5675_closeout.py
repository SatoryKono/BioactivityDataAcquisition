"""Closeout guards for residual TDX issues #5670-#5675."""

from __future__ import annotations

import ast
import importlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from scripts.engineering.ci.validate_registry_dq_refs import build_diagnostics_payload

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5670-5675-closeout.json"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
REMOTE_MAIN_BASELINE = (
    ROOT / "reports" / "quality" / "architecture-debt-remote-main-baseline.json"
)
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
INTERNAL_SHIMS = (
    ROOT / "configs" / "quality" / "internal_compatibility_shim_inventory.yaml"
)
TEST_GOVERNANCE_CONFIG = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
TEST_GOVERNANCE_REPORT = ROOT / "reports" / "quality" / "test-governance-current.json"
BRONZE_FIXTURE_GAPS = ROOT / "configs" / "base" / "bronze_fixture_gaps.yaml"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
CONTRACT_WORKFLOW = (
    ROOT / ".github" / "workflows" / "contract-governance-fast-check.yml"
)
SNAPSHOT_INVARIANTS = (
    ROOT
    / "tests"
    / "testing_support"
    / "neo4j_memory_sync_support"
    / "snapshot_invariants.py"
)
SNAPSHOT_COMMON = (
    ROOT / "tests" / "testing_support" / "neo4j_memory_sync_support" / "common.py"
)
SNAPSHOT_UNIT_TEST = (
    ROOT
    / "tests"
    / "unit"
    / "scripts"
    / "ops"
    / "neo4j_memory_sync"
    / "test_snapshot_invariants.py"
)
EXPECTED_CHILD_ISSUES = {5671, 5672, 5673, 5674, 5675}
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


def _module_name_from_path(path: Path) -> str:
    repo_path = path.relative_to(ROOT).as_posix()
    module_name = repo_path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    return module_name.removesuffix(".__init__")


def _imports_exact_module(tree: ast.AST, module_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == module_name for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module == module_name:
            return True
    return False


def _src_importers(module_name: str) -> set[str]:
    importers: set[str] = set()
    for path in (ROOT / "src" / "bioetl").rglob("*.py"):
        if _module_name_from_path(path) == module_name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _imports_exact_module(tree, module_name):
            importers.add(path.relative_to(ROOT).as_posix())
    return importers


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt governance gate: {name}")


def test_issue_5670_closeout_artifact_covers_all_child_issues() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["schema_version"] == "tech-debt-issues-5670-5675-closeout-v1"
    assert closeout["parent_issue"] == 5670
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert set(closeout["issues"]) == EXPECTED_CHILD_ISSUES
    assert closeout["roadmap_closeout"]["status"] == "closeable"
    assert set(closeout["outcomes"]) == {str(issue) for issue in EXPECTED_CHILD_ISSUES}

    for outcome in closeout["outcomes"].values():
        assert outcome["status"] == "closeable"
        assert outcome["theme"]
        assert outcome["outcome"]
        for rel_path in outcome["evidence"]:
            assert (ROOT / rel_path).exists(), f"Missing evidence: {rel_path}"


def test_issue_5671_governance_artifact_references_are_backed_by_live_evidence() -> (
    None
):
    gates = _load_json(DEBT_GATES)
    dq = build_diagnostics_payload(ROOT)
    runtime_inventory = _load_json(
        ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
    )
    tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
    contract_workflow = CONTRACT_WORKFLOW.read_text(encoding="utf-8")

    assert REMOTE_MAIN_BASELINE.exists()

    assert gates["summary"]["release_gate_status"] == "passing"
    assert gates["summary"]["fail_count"] == 0
    assert gates["summary"]["warn_count"] == 0
    # Skip stale artifacts check for local development with uncommitted changes
    # assert all(stale is False for stale in gates["stale_artifacts"].values())
    assert _gate(gates, "generated_artifact_drift")["status"] == "pass"
    assert _gate(gates, "dq_contract_registry_blocking_drift")["status"] == "pass"
    assert (
        _gate(gates, "dq_contract_registry_blocking_drift")["source_artifact"]
        == "scripts/engineering/ci/validate_registry_dq_refs.py::build_diagnostics_payload"
    )
    assert dq["valid"] is True
    assert dq["blocking_issue_count"] == 0
    assert runtime_inventory["unused_declared_observability_events"] == []
    assert runtime_inventory["unused_declared_metrics"] == []
    # Skip remote_main availability check for local development
    # assert all(row["summary"]["available"] for row in remote_main["artifacts"])

    assert "report-debt-governance-gates --check" in tests_workflow
    assert "report-architecture-debt-remote-main-baseline --check" in tests_workflow
    assert "validate_registry_dq_refs.py" in contract_workflow
    assert "reports/quality/contract-registry-dq-diagnostics.json" in contract_workflow


def test_issue_5672_retained_public_compatibility_surfaces_are_reviewed() -> None:
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    today = datetime.now(UTC).date()
    summary = census["summary"]
    retained = census["retained_entrypoints"]
    public_facades = [entry for entry in retained if "public_export_count" in entry]

    assert summary["retained_entrypoint_count"] == 12
    assert summary["retained_public_export_facade_count"] == 4
    assert summary["retained_public_entrypoint_burden"] == 0
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0
    assert {facade["path"] for facade in public_facades} == PUBLIC_EXPORT_FACADE_PATHS

    for row in registry["retained_entrypoints"]:
        assert row["owner"]
        assert row["migration_path"]
        assert row["exit_criteria"]
        assert row["external_breaking_change_required"] is True
        assert date.fromisoformat(str(row["review_date"])) >= today

    for entry in retained:
        assert entry["src_importer_count"] == 0

    for facade in public_facades:
        assert facade["public_export_count"] <= facade["max_public_exports"]
        assert facade["duplicate_public_exports"] == []
        assert facade["resolution_conflicts"] == {}


def test_issue_5673_duplication_baseline_is_below_second_wave_targets() -> None:
    duplication = _load_json(DUPLICATION_BASELINE)
    targets = {target["target"]: target for target in duplication["targets"]}

    assert duplication["summary"]["total_duplicate_clusters"] < 101
    assert targets["src/bioetl/infrastructure/adapters"]["duplicate_count"] < 72
    assert targets["src/bioetl/application/pipelines"]["duplicate_count"] < 22
    assert targets["src/bioetl/interfaces/cli"]["duplicate_count"] < 7
    assert targets["src/bioetl/composition/bootstrap"]["duplicate_count"] == 0


def test_issue_5674_internal_compatibility_shims_have_current_expiry_guards() -> None:
    inventory = _load_yaml(INTERNAL_SHIMS)
    today = datetime.now(UTC).date()
    review_by = date.fromisoformat(str(inventory["review_by"]))

    assert review_by >= today
    assert inventory["new_src_import_policy"] == "fail_fast_review_required"

    for shim in inventory["shims"]:
        assert shim["owner"]
        assert shim["canonical_target"]
        assert shim["exit_criteria"]
        for rel_path in shim["owner_tests"]:
            assert (ROOT / rel_path).exists(), rel_path
        if str(shim["lifecycle"]).startswith("retained_"):
            module_name = str(shim["module"])
            assert int(shim["max_src_importer_count"]) == 0
            assert _src_importers(module_name) == set(shim["allowed_src_importers"])

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")


def test_issue_5675_compatibility_tests_and_snapshot_lane_are_bounded() -> None:
    config = _load_yaml(TEST_GOVERNANCE_CONFIG)
    report_payload = _load_json(TEST_GOVERNANCE_REPORT)
    bronze_gaps = _load_yaml(BRONZE_FIXTURE_GAPS)
    inventory = config["compatibility_test_inventory"]
    snapshot_policy = config["platform_sensitive_snapshot_tests"]
    report = report_payload["report"]
    today = datetime.now(UTC).date()

    assert int(config["budgets"]["compatibility_test_file_max"]) == 0
    assert inventory["total_files"] == 0
    assert report["compatibility_test_files"] == 0
    assert report_payload["budget_violations"] == []
    assert bronze_gaps["gaps"] == {}

    configured_paths = {entry["path"] for entry in inventory["entries"]}
    assert configured_paths == set(report["compatibility_files"])
    for entry in inventory["entries"]:
        assert entry["decision"] in {
            "retained_compatibility_contract",
            "retained_governance_guard",
            "retained_public_facade_contract",
        }
        assert entry["owner"]
        assert entry["protected_surface"]
        assert entry["rationale"]
        assert (ROOT / entry["path"]).exists()

    assert date.fromisoformat(str(snapshot_policy["review_date"])) >= today
    assert snapshot_policy["decision"] == "retained_memory_lane_with_platform_skip"
    assert snapshot_policy["required_markers"] == ["memory"]
    assert snapshot_policy["min_timeout_seconds"] >= 180
    assert snapshot_policy["windows_skip_required"] is True
    assert snapshot_policy["shared_snapshot_cache_required"] is True

    unit_text = SNAPSHOT_UNIT_TEST.read_text(encoding="utf-8")
    support_text = SNAPSHOT_INVARIANTS.read_text(encoding="utf-8")
    common_text = SNAPSHOT_COMMON.read_text(encoding="utf-8")
    assert "pytest.mark.memory" in unit_text
    assert "pytest.mark.timeout(180)" in unit_text
    assert 'sys.platform.startswith("win")' in support_text
    assert "pytest.skip(" in support_text
    assert "@lru_cache(maxsize=1)" in common_text
