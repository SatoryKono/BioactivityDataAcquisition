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
"""Closeout guards for test-system issues #5729 through #5733."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5729-5733-closeout.json"
TELEMETRY_BASELINE = ROOT / "configs" / "quality" / "test_telemetry_baseline.yaml"
TELEMETRY_COVERAGE = ROOT / "reports" / "test-telemetry" / "coverage-summary.json"
TELEMETRY_SLOWEST = ROOT / "reports" / "test-telemetry" / "slowest-tests.json"
TEST_GOVERNANCE = ROOT / "reports" / "quality" / "test-governance-current.json"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
RUNNER_RUNTIME_MODE_TESTS = (
    ROOT
    / "tests"
    / "unit"
    / "composition"
    / "runtime_builders"
    / "test_runner_builder_runtime_modes.py"
)

EXPECTED_ISSUES = {5729, 5730, 5731, 5732, 5733}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5729_test_telemetry_artifacts_match_current_head() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5729"]
    baseline = _load_yaml(TELEMETRY_BASELINE)
    coverage = _load_json(TELEMETRY_COVERAGE)
    slowest = _load_json(TELEMETRY_SLOWEST)

    assert baseline["source_commit"] == outcome["source_commit"]
    assert coverage["source_commit"] == outcome["source_commit"]
    assert slowest["source_commit"] == outcome["source_commit"]
    assert baseline["source_run_id"] == outcome["source_run_id"]
    assert coverage["source_run_id"] == outcome["source_run_id"]
    assert slowest["source_run_id"] == outcome["source_run_id"]
    assert baseline["refreshed_at_utc"] == outcome["refreshed_at_utc"]
    assert coverage["refreshed_at_utc"] == outcome["refreshed_at_utc"]
    assert slowest["refreshed_at_utc"] == outcome["refreshed_at_utc"]
    assert baseline["coverage"]["actual_percent"] == outcome["coverage_actual_percent"]


def test_issue_5730_storage_and_control_plane_coverage_tail_is_below_floor() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5730"]
    coverage = _load_json(MODULE_COVERAGE)
    modules = {
        row["module"]: row
        for row in coverage["modules"]
        if row["module"] in outcome["target_modules"]
    }

    assert set(modules) == set(outcome["target_modules"])
    for module in outcome["target_modules"]:
        assert (
            modules[module]["coverage_percent"] >= outcome["minimum_coverage_percent"]
        )


def test_issue_5731_runner_and_observer_branch_gaps_are_closed() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5731"]
    coverage = _load_json(MODULE_COVERAGE)
    modules = {row["module"]: row for row in coverage["modules"]}

    for module, minimum in outcome["minimum_module_coverages"].items():
        assert modules[module]["coverage_percent"] >= minimum


def test_issue_5732_assertless_contract_inventory_is_reduced() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5732"]
    governance = _load_json(TEST_GOVERNANCE)
    report = governance["report"]
    summary = governance["summary"]
    families = report["assertless_candidates"]

    assert (
        report["assertless_total_candidates"] == outcome["assertless_total_candidates"]
    )
    assert (
        summary["intentional_no_exception_contract"]
        == outcome["intentional_no_exception_contract"]
    )
    file_family_counts: dict[str, int] = {}
    for candidate in families:
        file_family_counts[candidate["path"]] = (
            file_family_counts.get(candidate["path"], 0) + 1
        )
    for file_path, expected_count in outcome["target_file_family_counts"].items():
        assert file_family_counts[file_path] == expected_count


def test_issue_5733_heavy_runtime_mode_bootstrap_tests_are_removed_from_hotspot_file() -> (
    None
):
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5733"]
    text = RUNNER_RUNTIME_MODE_TESTS.read_text(encoding="utf-8")
    slowest = _load_json(TELEMETRY_SLOWEST)

    for removed_test_name in outcome["removed_full_bootstrap_tests"]:
        assert removed_test_name not in text
    assert not any(
        row["test"] == outcome["retired_hotspot_test"] for row in slowest["top_slowest"]
    )
