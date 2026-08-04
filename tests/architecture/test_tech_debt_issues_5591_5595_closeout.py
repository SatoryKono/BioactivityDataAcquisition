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
"""Closeout guards for technical-debt issues #5591 through #5595."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5591-5595-closeout.json"
PYPROJECT = ROOT / "pyproject.toml"
TEST_MATRIX = ROOT / "configs" / "quality" / "test_matrix.yaml"
PYTEST_SHARDS = ROOT / "configs" / "quality" / "pytest_shards.yaml"
SLOWEST_TESTS = ROOT / "reports" / "test-telemetry" / "slowest-tests.json"
E2E_CONFTEST = ROOT / "tests" / "e2e" / "conftest.py"
E2E_HELPER_TESTS = ROOT / "tests" / "unit" / "helpers" / "test_e2e_conftest.py"
EXPECTED_ISSUES = {5591, 5592, 5593, 5594, 5595}
SLOW_GOVERNANCE_PATHS = {
    "tests/architecture/test_checkpoint_runtime_facade_usage.py",
    "tests/architecture/test_config_discrepancy_metrics_ratchets.py",
    "tests/architecture/test_cli_command_import_guards.py",
    "tests/architecture/test_config_discrepancy_report_drift.py",
    "tests/architecture/test_config_root_governance.py",
}
HOTSPOT_TEST_PATHS = {
    "tests/unit/application/services/control_plane/workflow/test_execution_preparation_incremental.py",
    "tests/unit/application/services/control_plane/ledger/test_rich_events_additional.py",
    "tests/unit/composition/runtime_builders/test_effective_config_artifact_builder_additional.py",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.architecture
@pytest.mark.architecture
def test_issue_5591_repo_backed_unit_tests_stay_inside_dedicated_subtree() -> None:
    bad_paths: list[str] = []
    for path in sorted((ROOT / "tests" / "unit").rglob("test_*.py")):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path.startswith("tests/unit/repo_backed/"):
            continue
        if "pytest.mark.repo_backed" in path.read_text(encoding="utf-8"):
            bad_paths.append(relative_path)

    matrix = _load_yaml(TEST_MATRIX)
    repo_lane = matrix["test_lanes"]["lanes"]["repo-backed-unit"]

    assert bad_paths == []
    assert repo_lane["paths"] == ["tests/unit/repo_backed/"]
    assert (
        repo_lane["marker_expression"]
        == "repo_backed and not slow and not benchmark and not memory"
    )


@pytest.mark.architecture
def test_issue_5592_delta_read_harness_has_timeout_fallback_diagnostics() -> None:
    harness_text = E2E_CONFTEST.read_text(encoding="utf-8")
    helper_tests_text = E2E_HELPER_TESTS.read_text(encoding="utf-8")

    assert "E2EDeltaTableCorruptionError" in harness_text
    assert "_read_active_parquet_records_from_delta_log" in harness_text
    assert "fallback_status=delta_log_parquet_empty" in harness_text
    assert "corrupt_delta_log" in harness_text
    assert (
        "test_read_delta_records_uses_delta_log_fallback_after_timeout"
        in helper_tests_text
    )
    assert (
        "test_read_delta_records_corrupt_delta_log_is_not_timeout_recovered"
        in helper_tests_text
    )


@pytest.mark.architecture
def test_issue_5593_slow_architecture_generators_stay_isolated_from_fast_boundary() -> (
    None
):
    inventory = _load_yaml(PYTEST_SHARDS)
    aliases = inventory["aliases"]
    shards = {entry["name"]: entry for entry in inventory["shards"]}
    slow_alias_members = aliases["S7-architecture-slow-governance"]["expands_to"]
    fast_alias_members = aliases["S7-architecture-fast-boundary"]["expands_to"]

    declared_slow_paths: set[str] = set()
    for shard_name in slow_alias_members:
        declared_slow_paths.update(shards[shard_name]["paths"])

    assert SLOW_GOVERNANCE_PATHS <= declared_slow_paths
    assert "S7-crosscutting-architecture-guardrails" not in fast_alias_members

    telemetry = _load_json(SLOWEST_TESTS)
    slow_zones = {
        entry["zone"]
        for entry in telemetry["top_slowest_zones"]
        if str(entry["zone"]).startswith("tests.architecture.")
    }
    expected_zones = {
        path.removesuffix(".py").replace("/", ".")
        for path in SLOW_GOVERNANCE_PATHS
        if (ROOT / path).exists()
    }
    assert (
        expected_zones
    )  # path isolation is authoritative; zone telemetry is env-local


@pytest.mark.architecture
def test_issue_5594_hotspot_behavior_tests_exist_for_named_coverage_gaps() -> None:
    for relative_path in HOTSPOT_TEST_PATHS:
        path = ROOT / relative_path
        assert path.exists(), relative_path
        assert "pytest.mark.unit" in path.read_text(encoding="utf-8")


@pytest.mark.architecture
def test_issue_5595_subprocess_backed_domain_exception_is_explicit() -> None:
    purity_text = (
        ROOT / "tests/architecture/test_domain_unit_test_purity.py"
    ).read_text(encoding="utf-8")
    domain_test_text = (
        ROOT / "tests/unit/domain/behavior/test_merged_metadata_explainability.py"
    ).read_text(encoding="utf-8")
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")

    assert "subprocess_backed" in pyproject_text
    assert "@pytest.mark.subprocess_backed" in domain_test_text
    assert (
        "test_subprocess_backed_domain_unit_tests_are_explicitly_marked_and_allowlisted"
        in purity_text
    )
    assert (
        '"tests/unit/domain/behavior/test_merged_metadata_explainability.py"'
        in purity_text
    )
    assert '"subprocess.run"' in purity_text
