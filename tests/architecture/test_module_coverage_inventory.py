"""Architecture guardrails for committed module-level coverage inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa.report_module_coverage_inventory import (
    _iter_source_modules,
    compute_source_tree_sha256,
    main as module_coverage_inventory_main,
)
from tests.architecture._test_matrix_policy_support import load_matrix

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "tests.yml"
SCORECARD_PATH = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
GATES_PATH = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"


@pytest.mark.architecture
def test_module_coverage_inventory_is_committed_and_shape_is_stable() -> None:
    assert INVENTORY_PATH.exists()
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert committed["schema_version"] == 1
    assert committed["generated_by"].endswith("report_module_coverage_inventory.py")
    assert committed["coverage_xml_path"] == "reports/coverage/coverage.xml"
    assert committed["measurement_mode"] == "coverage_xml"
    assert (
        isinstance(committed["coverage_xml_sha256"], str)
        and committed["coverage_xml_sha256"]
    )
    assert committed["canonical_coverage_lane"] == "coverage-verify"
    assert isinstance(committed["modules"], list) and committed["modules"]
    assert committed["summary"]["coverage_xml_present"] is True
    assert isinstance(committed["summary"]["unmeasured_module_count"], int)
    assert isinstance(committed["summary"]["unmeasured_modules"], list)
    assert committed["summary"]["unmeasured_module_count"] == len(
        committed["summary"]["unmeasured_modules"]
    )
    for unmeasured in committed["summary"]["unmeasured_modules"]:
        assert str(unmeasured["module"]).startswith("bioetl")
        assert str(unmeasured["path"]).startswith("src/bioetl/")
        assert unmeasured["reason"] == "coverage_xml_has_no_class_entry"
    hotspot_family_coverage = committed["summary"]["hotspot_family_coverage"]
    assert isinstance(hotspot_family_coverage, dict) and hotspot_family_coverage

    for row in committed["modules"]:
        assert row["module"].startswith("bioetl")
        assert str(row["path"]).startswith("src/bioetl/")
        assert isinstance(row["source_lines"], int) and row["source_lines"] >= 0
        assert row["coverage_status"] in {
            "coverage_xml_missing",
            "unmeasured",
            "no_executable_lines",
            "uncovered",
            "fully_covered",
            "partially_covered",
        }
        coverage_percent = row["coverage_percent"]
        if coverage_percent is not None:
            assert 0.0 <= coverage_percent <= 100.0

    for family_row in hotspot_family_coverage.values():
        assert isinstance(family_row["module_count"], int)
        assert isinstance(family_row["measured_module_count"], int)
        assert isinstance(family_row["covered_module_count"], int)
        assert isinstance(family_row["unmeasured_module_count"], int)
        assert isinstance(family_row["allowlisted_unmeasured_module_count"], int)
        assert isinstance(family_row["unexpected_unmeasured_module_count"], int)
        assert isinstance(family_row["allowlisted_unmeasured_modules"], list)
        assert isinstance(family_row["unexpected_unmeasured_modules"], list)
        assert isinstance(family_row["measured_percent"], float)
        assert 0.0 <= family_row["measured_percent"] <= 100.0
        assert isinstance(family_row["status_counts"], dict)
        assert isinstance(family_row["thresholds"], dict)
        assert family_row["threshold_status"] in {"pass", "fail"}
        coverage_percent_min = family_row["coverage_percent_min"]
        coverage_percent_avg = family_row["coverage_percent_avg"]
        covered_line_percent = family_row["covered_line_percent"]
        if coverage_percent_min is not None:
            assert 0.0 <= coverage_percent_min <= 100.0
        if coverage_percent_avg is not None:
            assert 0.0 <= coverage_percent_avg <= 100.0
        if covered_line_percent is not None:
            assert 0.0 <= covered_line_percent <= 100.0
        assert family_row["module_count"] >= family_row["measured_module_count"]
        assert family_row["module_count"] >= family_row["covered_module_count"]
        assert family_row["module_count"] >= family_row["unmeasured_module_count"]
        assert family_row["unmeasured_module_count"] == (
            family_row["allowlisted_unmeasured_module_count"]
            + family_row["unexpected_unmeasured_module_count"]
        )


@pytest.mark.architecture
def test_module_coverage_inventory_covers_every_source_module() -> None:
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    inventory_paths = {str(row["path"]) for row in committed["modules"]}
    expected_paths = {
        path.relative_to(ROOT).as_posix() for path in _iter_source_modules(ROOT)
    }

    assert inventory_paths == expected_paths


@pytest.mark.architecture
def test_module_coverage_inventory_source_tree_hash_is_current() -> None:
    # Skip on WSL due to slow filesystem performance causing hash computation timeout
    try:
        with open("/proc/version", "r") as f:
            if "microsoft" in f.read().lower():
                pytest.skip("Skipped on WSL due to filesystem performance")
    except (OSError, IOError):
        pass

    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert committed["source_tree_sha256"] == compute_source_tree_sha256(repo_root=ROOT)


@pytest.mark.architecture
def test_module_coverage_inventory_reports_measured_hotspot_family_evidence() -> None:
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    hotspot_family_coverage = committed["summary"]["hotspot_family_coverage"]
    assert isinstance(hotspot_family_coverage, dict)

    for family_name in (
        "application_core",
        "composition_bootstrap_runtime",
        "composition_factories_pipeline",
        "application_services_control_plane",
        "composition_runtime_builders",
    ):
        family_row = hotspot_family_coverage.get(family_name)
        assert isinstance(family_row, dict), family_name
        assert family_row["module_count"] > 0, family_name
        assert family_row["unexpected_unmeasured_module_count"] == 0, family_name
        assert family_row["unexpected_unmeasured_modules"] == [], family_name
        assert (
            family_row["measured_module_count"]
            + family_row["allowlisted_unmeasured_module_count"]
            == family_row["module_count"]
        ), family_name
        thresholds = family_row["thresholds"]
        assert (
            family_row["covered_module_count"] >= thresholds["min_covered_module_count"]
        )
        assert (
            family_row["covered_line_percent"] >= thresholds["min_covered_line_percent"]
        )
        assert family_row["threshold_status"] == "pass", family_name


@pytest.mark.architecture
def test_hotspot_refactor_targets_have_authoritative_module_coverage_gates() -> None:
    """Hotspot refactor families must have an explicit module-level coverage gate."""
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    hotspot_family_coverage = committed["summary"]["hotspot_family_coverage"]
    scorecard = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    gate = scorecard["hotspot_family_coverage_thresholds"]

    assert gate["mode"] == "fail-fast"
    assert gate["enforcement_issue"] == "#5036"
    assert gate["authoritative_for_hotspot_refactor_readiness"] is True
    assert gate["authoritative_artifact"] == (
        "reports/quality/module-coverage-inventory.json"
    )
    assert gate["canonical_lane"] == "coverage-verify"
    assert isinstance(gate["readiness_policy"], str) and gate["readiness_policy"]

    gated_families = gate["families"]
    assert set(gated_families) == set(hotspot_family_coverage)
    for family_name, thresholds in gated_families.items():
        family_row = hotspot_family_coverage[family_name]
        assert family_row["thresholds"] == thresholds
        assert family_row["threshold_status"] == "pass", family_name


@pytest.mark.architecture
def test_module_coverage_inventory_check_requires_coverage_xml_by_default(
    tmp_path: Path,
) -> None:
    missing_coverage_xml = tmp_path / "coverage.xml"
    artifact = tmp_path / "module-coverage-inventory.json"
    artifact.write_text("{}", encoding="utf-8")

    rc = module_coverage_inventory_main(
        [
            "--repo-root",
            str(ROOT),
            "--coverage-xml",
            str(missing_coverage_xml),
            "--json-out",
            str(artifact),
            "--check",
        ]
    )

    assert rc == 1


@pytest.mark.architecture
def test_module_coverage_inventory_generation_requires_coverage_xml_by_default(
    tmp_path: Path,
) -> None:
    missing_coverage_xml = tmp_path / "coverage.xml"
    artifact = tmp_path / "module-coverage-inventory.json"

    rc = module_coverage_inventory_main(
        [
            "--repo-root",
            str(ROOT),
            "--coverage-xml",
            str(missing_coverage_xml),
            "--json-out",
            str(artifact),
        ]
    )

    assert rc == 1
    assert not artifact.exists()


@pytest.mark.architecture
def test_coverage_verify_workflow_generates_module_coverage_inventory() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "coverage xml -o reports/coverage/coverage.xml" in workflow
    assert "report-module-coverage" in workflow
    assert "reports/quality/module-coverage-inventory.json" in workflow


@pytest.mark.architecture
def test_module_coverage_gates_policy_is_committed() -> None:
    assert GATES_PATH.exists()
    gates = yaml.safe_load(GATES_PATH.read_text(encoding="utf-8"))
    assert gates["schema_version"] == 1
    assert gates["enforcement"]["default_mode"] == "block-regression"
    assert "aggregates_and_contracts" in gates["tiers"]
    assert gates["tiers"]["aggregates_and_contracts"]["line_min_percent"] == 95


@pytest.mark.architecture
def test_test_matrix_declares_module_coverage_inventory_contract() -> None:
    matrix = load_matrix()
    inventory = matrix["module_coverage_inventory"]
    coverage_lane = matrix["test_lanes"]["lanes"]["coverage-verify"]

    assert inventory["enabled"] is True
    assert inventory["canonical_lane"] == "coverage-verify"
    assert inventory["generator"] == (
        "scripts/engineering/qa/report_module_coverage_inventory.py"
    )
    assert inventory["authoritative_status_source"] == "live_ci_coverage_verify"
    assert (
        inventory["committed_artifact_refresh_policy"]
        == "green_coverage_verify_run_only"
    )
    assert inventory["artifact"] == "reports/quality/module-coverage-inventory.json"
    assert inventory["coverage_xml"] == "reports/coverage/coverage.xml"
    assert inventory["canonical_generation_requires_coverage_xml"] is True
    per_module_gates = inventory["per_module_gates"]
    assert per_module_gates["enabled"] is True
    assert per_module_gates["enforcement_mode"] == "block-regression"
    assert per_module_gates["policy"] == "configs/quality/module_coverage_gates.yaml"
    assert (
        coverage_lane["expected_artifacts"]["module_coverage_inventory"]
        == (inventory["artifact"])
    )
