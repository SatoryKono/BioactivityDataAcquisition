"""Architecture guardrails for committed module-level coverage inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.file_discovery import discover_files
from tests.architecture._test_matrix_policy_support import load_matrix

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "tests.yml"


@pytest.mark.architecture
def test_module_coverage_inventory_is_committed_and_shape_is_stable() -> None:
    assert INVENTORY_PATH.exists()
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert committed["schema_version"] == 1
    assert committed["generated_by"].endswith("report_module_coverage_inventory.py")
    assert committed["coverage_xml_path"] == "reports/coverage/coverage.xml"
    assert committed["canonical_coverage_lane"] == "coverage-verify"
    assert isinstance(committed["modules"], list) and committed["modules"]

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


@pytest.mark.architecture
def test_module_coverage_inventory_covers_every_source_module() -> None:
    committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    inventory_paths = {str(row["path"]) for row in committed["modules"]}
    source_root = ROOT / "src" / "bioetl"
    expected_paths = {
        f"src/bioetl/{relative_path}"
        for relative_path in discover_files(str(source_root.resolve()), ".py")
    }

    assert inventory_paths == expected_paths


@pytest.mark.architecture
def test_coverage_verify_workflow_generates_module_coverage_inventory() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "coverage xml -o reports/coverage/coverage.xml" in workflow
    assert "report-module-coverage" in workflow
    assert "reports/quality/module-coverage-inventory.json" in workflow


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
    assert inventory["artifact"] == "reports/quality/module-coverage-inventory.json"
    assert inventory["coverage_xml"] == "reports/coverage/coverage.xml"
    assert (
        coverage_lane["expected_artifacts"]["module_coverage_inventory"]
        == (inventory["artifact"])
    )
