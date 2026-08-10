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
"""Architecture checks for CI heavy-lane rebalancing."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "ci_heavy_lane_rebalance.yaml"


def _load_policy() -> dict[str, object]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _read_workflow(policy: dict[str, object]) -> str:
    return (ROOT / str(policy["workflow_path"])).read_text(encoding="utf-8")


def _job_block(workflow: str, job: str) -> str:
    # tests.yml uses 2-space job keys under `jobs:`.
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"workflow is missing job {job!r}"
    return match.group("body")


@pytest.mark.architecture
class TestCiHeavyLaneRebalance:
    """Keep expensive CI lanes aligned with their architectural purpose."""

    def test_policy_declares_heavy_lane_inventory_and_success_metrics(self) -> None:
        policy = _load_policy()

        assert policy["policy_scope"] == "ci_heavy_lane_rebalance"
        assert policy["workflow_path"] == ".github/workflows/tests.yml"
        assert policy["source_issue"] == 3329
        assert set(policy["success_metrics"]) == {
            "track_d_gate_scope",
            "coverage_verify_scope",
            "duration_telemetry",
        }

        lanes = {entry["job"]: entry for entry in policy["lanes"]}  # type: ignore[index]
        assert set(lanes) == {
            "track-d-gates",
            "control-plane-e2e",
            "test-matrix",
            "memory-tests",
            "performance-budgets",
            "coverage-verify",
        }
        for entry in lanes.values():
            assert entry["owner"]
            assert entry["classification"]
            assert entry["full_bootstrap_policy"]
            assert entry["retained_scenarios"]
            assert entry["telemetry_artifact"]

    def test_declared_heavy_lanes_exist_in_workflow(self) -> None:
        policy = _load_policy()
        workflow = _read_workflow(policy)

        for entry in policy["lanes"]:  # type: ignore[index]
            assert f"  {entry['job']}:" in workflow

    def test_track_d_gate_contains_only_runtime_linkage_suite(self) -> None:
        policy = _load_policy()
        workflow = _read_workflow(policy)
        track_d = next(
            entry
            for entry in policy["lanes"]
            if entry["job"] == "track-d-gates"  # type: ignore[index]
        )
        block = _job_block(workflow, "track-d-gates")

        retained_paths = {
            scenario["path"] for scenario in track_d["retained_scenarios"]
        }
        assert retained_paths == {
            "tests/integration/ci/test_track_d_fixture_control_plane_linkage.py"
        }
        assert (
            "tests/integration/ci/test_track_d_fixture_control_plane_linkage.py"
            in block
        )
        assert "tests/unit/" not in block
        assert "tests/architecture/" not in block

        for scenario in track_d["relocated_scenarios"]:
            assert scenario["path"] not in block
            assert scenario["new_lane"] == "test-fast"

    def test_coverage_verify_remains_serial_subset_not_full_suite_rerun(self) -> None:
        policy = _load_policy()
        workflow = _read_workflow(policy)
        block = _job_block(workflow, "coverage-verify")
        metric = policy["success_metrics"]["coverage_verify_scope"]  # type: ignore[index]

        assert f'--parallel-marker "{metric["serial_marker"]}"' in block
        for excluded_path in metric["known_exclusions"]:
            assert f"--ignore={excluded_path}" in block
        assert "--skip-serial-pass" in block
        assert "coverage combine --keep reports/coverage" in block

    def test_memory_and_performance_lanes_stay_isolated(self) -> None:
        policy = _load_policy()
        workflow = _read_workflow(policy)
        memory_block = _job_block(workflow, "memory-tests")
        performance_block = _job_block(workflow, "performance-budgets")
        matrix_block = _job_block(workflow, "test-matrix")

        assert '-m "memory"' in memory_block
        assert "--junitxml=reports/test-telemetry/junit-memory.xml" in memory_block
        assert "tests/performance/test_hotspot_budgets.py" in performance_block
        assert '-m "benchmark and performance"' in performance_block
        assert '-m "not serial and not memory"' in matrix_block

    def test_duration_telemetry_consumes_rebalanced_lane_artifacts(self) -> None:
        policy = _load_policy()
        workflow = _read_workflow(policy)
        block = _job_block(workflow, "duration-telemetry")
        metric = policy["success_metrics"]["duration_telemetry"]  # type: ignore[index]

        assert "name: test-duration-telemetry" in block
        for artifact in metric["required_inputs"]:
            assert artifact in workflow
        assert "junit-track-d.xml" in block
        assert "junit-memory.xml" in block
