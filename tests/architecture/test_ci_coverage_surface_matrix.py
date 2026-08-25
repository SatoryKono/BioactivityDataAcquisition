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
"""Architecture tests for the tracked CI coverage surface matrix."""

from __future__ import annotations

import re
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


def _job_block(workflow: str, job: str) -> str:
    # tests.yml uses 2-space job keys under `jobs:`.
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"workflow is missing mapped job '{job}'"
    return match.group("body")


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
        assert (
            matrix.get("confidence_accounting", {}).get("first_class_confidence")
            is True
        )
        assert matrix.get("confidence_accounting", {}).get("hard_threshold_gate") == (
            "coverage-verify"
        )

    def test_ci_coverage_surface_matrix_tracks_expected_major_lanes(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        jobs = {entry["job"] for entry in matrix.get("lanes", [])}

        assert jobs == {
            "smoke-check",
            "control-plane-e2e",
            "contract-confidence",
            "track-d-gates",
            "memory-tests",
            "test-fast",
            "repo-backed-unit",
            "unit-scripts-tooling",
            "test-matrix",
            "coverage-verify",
            "coverage-inventory-currentness",
            "duration-telemetry",
        }

    def test_workflow_and_matrix_agree_on_coverage_roles(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}

        for job in entries:
            assert f"{job}:" in workflow, f"workflow is missing mapped job '{job}'"

        coverage_shard_jobs = {
            "smoke-check",
            "contract-confidence",
            "repo-backed-unit",
            "unit-scripts-tooling",
            "test-matrix",
        }
        for job in coverage_shard_jobs:
            entry = entries[job]
            assert entry["lane_type"] == "coverage_shard"
            assert entry["emits_coverage_artifact"] is True
            assert entry["participates_in_hard_threshold"] is True
            assert entry["threshold_enforced_in_job"] is False

        coverage_verify = entries["coverage-verify"]
        assert coverage_verify["lane_type"] == "hard_threshold_gate"
        assert coverage_verify["downloads_coverage_artifacts"] is True
        assert coverage_verify["threshold_enforced_in_job"] is True
        assert coverage_verify["participates_in_hard_threshold"] is True

        currentness = entries["coverage-inventory-currentness"]
        assert currentness["lane_type"] == "artifact_currentness_gate"
        assert currentness["downloads_coverage_artifacts"] is True
        assert currentness["threshold_enforced_in_job"] is False
        assert currentness["participates_in_hard_threshold"] is False

        execution_only_jobs = {
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

        assert "name: coverage-data-smoke" in workflow
        assert "name: coverage-data-contract-confidence" in workflow
        assert "name: coverage-data-repo-backed-unit" in workflow
        assert "name: coverage-data-unit-scripts-tooling" in workflow
        assert "name: coverage-data-fast" not in workflow
        assert "name: coverage-data-control-plane-e2e" not in workflow
        assert "name: coverage-data-memory" not in workflow
        assert "name: coverage-data-${{ matrix.test-group.name }}" in workflow
        assert "pattern: coverage-data-*" in workflow
        assert "coverage report --show-missing --fail-under=85" in workflow
        assert "test-telemetry-memory" in workflow
        assert "junit-memory.xml" in workflow
        assert "test-telemetry-contract-confidence" in workflow
        assert "junit-contract-confidence.xml" in workflow

        coverage_verify = entries["coverage-verify"]
        for excluded_path in coverage_verify.get("known_exclusions", []):
            assert f"--ignore={excluded_path}" in workflow, (
                f"coverage-verify serial pass must keep excluding {excluded_path}"
            )

        assert "name: test-duration-telemetry" in workflow
        assert "control-plane-completeness" in workflow
        assert "junit-track-d.xml" in workflow

    def test_required_coverage_contributors_are_wired_fail_closed(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}
        aggregation = matrix["coverage_aggregation"]
        coverage_block = _job_block(workflow, "coverage-verify")

        assert "if: ${{ always() && !cancelled() }}" in coverage_block
        assert aggregation["artifact_pattern"] == "coverage-data-*"
        assert "pattern: coverage-data-*" in coverage_block
        for job in aggregation["required_upstream_jobs"]:
            assert f"- {job}" in coverage_block, (
                f"coverage-verify must need required coverage producer {job}"
            )

        for job in (
            "smoke-check",
            "contract-confidence",
            "repo-backed-unit",
            "unit-scripts-tooling",
        ):
            entry = entries[job]
            block = _job_block(workflow, job)
            assert entry["coverage_artifact"] in block
            assert entry["coverage_file"] in block
            assert "--cov=src/bioetl --cov-report=" in block
            assert 'cp .coverage "$COVERAGE_FILE"' in block
            assert 'if [ ! -s "$COVERAGE_FILE" ]' in block
            assert "include-hidden-files: true" in block
            assert "if-no-files-found: error" in block

        for shard in aggregation["required_blocking_lane_shards"]:
            assert shard in coverage_block, (
                f"coverage-verify must fail closed when {shard} is unavailable"
            )

        matrix_entry = entries["test-matrix"]
        matrix_block = _job_block(workflow, "test-matrix")
        matrix_shards = {
            "reports/coverage/.coverage.unit-domain",
            "reports/coverage/.coverage.unit-application",
            "reports/coverage/.coverage.unit-infrastructure",
            "reports/coverage/.coverage.unit-other",
            "reports/coverage/.coverage.integration",
            "reports/coverage/.coverage.security",
        }
        assert set(matrix_entry["coverage_files"]) == matrix_shards
        assert matrix_shards <= set(aggregation["required_blocking_lane_shards"])
        assert "if-no-files-found: error" in matrix_block

    def test_candidate_producer_and_currentness_gate_are_separate(self) -> None:
        """A green SHA-bound producer must remain usable for first refresh."""
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        producer = _job_block(workflow, "coverage-verify")
        currentness = _job_block(workflow, "coverage-inventory-currentness")

        assert "module-coverage-inventory.candidate.json" in producer
        assert "cmp --silent" not in producer
        assert producer.index("coverage xml") < producer.index(
            "report-module-coverage"
        )
        assert producer.index("report-module-coverage") < producer.index(
            "coverage report --show-missing --fail-under=85"
        )
        assert "needs: coverage-verify" in currentness
        assert "name: coverage-report" in currentness
        assert "cmp --silent" in currentness

    def test_blocking_confidence_lanes_have_required_assertions(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}

        required_jobs = set(
            matrix.get("confidence_lane_policy", {}).get("required_blocking_jobs", [])
        )
        assert (
            set(
                matrix.get("confidence_accounting", {}).get(
                    "blocking_confidence_lanes",
                    [],
                )
            )
            == required_jobs
        )
        assert required_jobs == {
            "contract-confidence",
            "control-plane-e2e",
            "memory-tests",
        }

        for job in sorted(required_jobs):
            entry = entries[job]
            assert entry["blocking_confidence_lane"] is True
            assert entry["threshold_enforced_in_job"] is False

            if job == "contract-confidence":
                assert entry["lane_type"] == "coverage_shard"
                assert entry["participates_in_hard_threshold"] is True
                assert entry["emits_coverage_artifact"] is True
            else:
                assert entry["lane_type"] == "execution_only"
                assert entry["participates_in_hard_threshold"] is False
                assert entry["emits_coverage_artifact"] is False

            block = _job_block(workflow, job)
            assertions = entry["blocking_assertions"]
            for expected in assertions["command_contains"]:
                assert expected in block, (
                    f"{job} is missing command assertion {expected}"
                )
            for expected in assertions["required_artifacts"]:
                assert expected in block, (
                    f"{job} is missing artifact assertion {expected}"
                )

        duration_block = _job_block(workflow, "duration-telemetry")
        assert "junit-contract-confidence.xml" in duration_block
        assert "--suite contracts" in duration_block

    def test_required_vcr_lanes_fail_closed_without_lfs_evidence(self) -> None:
        """Required VCR/LFS confidence surfaces must not soft-skip on LFS failure (#7493)."""
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])

        for job in ("vcr-preflight", "control-plane-e2e", "governance-preflight"):
            block = _job_block(workflow, job)
            assert "continue-on-error: true" not in block, (
                f"{job} must not continue-on-error for required LFS materialization"
            )
            assert "if: steps.lfs_pull.outcome" not in block, (
                f"{job} must not gate required steps on lfs_pull outcome"
            )
            assert "if: steps.governance_lfs_pull.outcome" not in block, (
                f"{job} must not gate required steps on governance_lfs_pull outcome"
            )
            assert "Skip VCR content gates when LFS budget is exhausted" not in block
            assert "Skip control-plane VCR smoke when LFS is unavailable" not in block
            assert (
                "Skip VCR-bound governance preflight when LFS is unavailable"
                not in block
            )
            assert "Fail-closed (#7493)" in block or "#7493" in block
            if job == "control-plane-e2e":
                assert "id: lfs_pull" in block
                assert "if-no-files-found: error" in block
                assert "::error::" in block

    def test_coverage_shard_python_versions_match_workflow(self) -> None:
        matrix = _load_yaml(MATRIX_PATH)
        workflow = _read_workflow(ROOT / matrix["workflow_path"])
        entries = {entry["job"]: entry for entry in matrix.get("lanes", [])}

        test_matrix = entries["test-matrix"]
        assert test_matrix["coverage_python_versions"] == ["3.13"]
        assert (
            "Upload coverage shard (${{ matrix.test-group.name }} on Python 3.13)"
            in workflow
        )
        assert "matrix.python-version == '3.13'" in workflow
