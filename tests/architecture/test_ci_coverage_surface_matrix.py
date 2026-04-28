"""Architecture tests for the tracked CI coverage surface matrix."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "configs" / "quality" / "ci_coverage_surface_matrix.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _read_workflow(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.architecture
class TestCiCoverageSurfaceMatrix:
    """Keep CI coverage-surface mapping explicit and synchronized with workflow reality."""

    def test_ci_coverage_surface_matrix_is_present_and_scoped(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)

        assert matrix.get("policy_scope") == "ci_coverage_surface_mapping"
        assert matrix.get("workflow_path") == ".github/workflows/tests.yml"
        assert matrix.get("threshold_policy", {}).get("hard_coverage_threshold") == 85
        assert (
            matrix.get("threshold_policy", {}).get("enforced_in_job")
            == "coverage-verify"
        )

    def test_ci_coverage_surface_matrix_tracks_expected_major_lanes(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        jobs = {entry["job"] for entry in matrix.get("lanes", [])}

        assert jobs == {
            "smoke-check",
            "control-plane-e2e",
            "track-d-gates",
            "memory-tests",
            "test-fast",
            "test-matrix",
            "coverage-verify",
            "duration-telemetry",
        }

    def test_workflow_and_matrix_agree_on_coverage_roles(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}

        for job in entries:
            assert f"{job}:" in workflow, f"workflow is missing mapped job '{job}'"

        matrix_entry = entries["test-matrix"]
        assert matrix_entry["lane_type"] == "coverage_shard"
        assert matrix_entry["emits_coverage_artifact"] is True
        assert matrix_entry["participates_in_hard_threshold"] is True
        assert matrix_entry["threshold_enforced_in_job"] is False

        coverage_verify = entries["coverage-verify"]
        assert coverage_verify["lane_type"] == "hard_threshold_gate"
        assert coverage_verify["downloads_coverage_artifacts"] is True
        assert coverage_verify["threshold_enforced_in_job"] is True
        assert coverage_verify["participates_in_hard_threshold"] is True

        execution_only_jobs = {
            "smoke-check",
            "control-plane-e2e",
            "track-d-gates",
            "memory-tests",
            "test-fast",
        }
        for job in execution_only_jobs:
            entry = entries[job]
            assert entry["lane_type"] == "execution_only"
            assert entry["emits_coverage_artifact"] is False
            assert entry["participates_in_hard_threshold"] is False
            assert entry["threshold_enforced_in_job"] is False

        telemetry = entries["duration-telemetry"]
        assert telemetry["lane_type"] == "telemetry_only"
        assert telemetry["emits_coverage_artifact"] is False
        assert telemetry["participates_in_hard_threshold"] is False
        assert telemetry["threshold_enforced_in_job"] is False

    def test_workflow_contains_expected_artifacts_and_exclusions(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}

        assert "name: coverage-data-smoke" not in workflow
        assert "name: coverage-data-fast" not in workflow
        assert "name: coverage-data-${{ matrix.test-group.name }}" in workflow
        assert "pattern: coverage-data-*" in workflow
        assert "coverage report --show-missing --fail-under=85" in workflow
        assert "test-telemetry-memory" in workflow
        assert "junit-memory.xml" in workflow

        coverage_verify = entries["coverage-verify"]
        for excluded_path in coverage_verify.get("known_exclusions", []):
            assert f"--ignore={excluded_path}" in workflow, (
                f"coverage-verify serial pass must keep excluding {excluded_path}"
            )

        assert "name: test-duration-telemetry" in workflow
        assert "control-plane-completeness" in workflow
        assert "junit-track-d.xml" in workflow

    def test_coverage_shard_python_versions_match_workflow(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}

        test_matrix = entries["test-matrix"]
        assert test_matrix["coverage_python_versions"] == ["3.12"]
        assert (
            "Upload coverage shard (${{ matrix.test-group.name }} on Python 3.12)"
            in workflow
        )
        assert "matrix.python-version == '3.12'" in workflow
