"""Architecture tests for lane, VCR, and baseline test-matrix policy."""

from __future__ import annotations

import tomllib

import pytest

from tests.architecture._test_matrix_policy_support import (
    ROOT,
    TESTS_DIR,
    contains_forbidden_hypothesis_usage,
    forbidden_test_dir,
    lane_paths,
    lane_runner,
    load_matrix,
    must_unit_layers,
    required_provider_names,
)


@pytest.mark.architecture
class TestVCRCassetteCoverage:
    """Validate VCR cassettes exist for required providers."""

    def test_vcr_dir_exists_for_each_provider(self) -> None:
        matrix = load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider in required_provider_names(matrix, "vcr_cassettes"):
            provider_vcr = vcr_dir / provider
            assert provider_vcr.is_dir(), (
                f"Missing VCR cassette directory for provider '{provider}': "
                f"{provider_vcr}"
            )

    def test_vcr_cassettes_not_empty(self) -> None:
        matrix = load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider in required_provider_names(matrix, "vcr_cassettes"):
            provider_vcr = vcr_dir / provider
            if provider_vcr.is_dir():
                cassettes = list(provider_vcr.glob("*.yaml"))
                assert cassettes, (
                    f"Provider '{provider}' VCR directory exists but has no cassettes"
                )


@pytest.mark.architecture
class TestPropertyTestBoundaries:
    """Validate property-based tests respect ADR-042 boundaries."""

    def test_no_hypothesis_in_forbidden_dirs(self) -> None:
        matrix = load_matrix()
        forbidden = matrix.get("property_test_boundaries", {}).get("forbidden", [])

        for forbidden_path in forbidden:
            test_dir = forbidden_test_dir(forbidden_path)
            if not test_dir.is_dir():
                continue

            for test_file in test_dir.rglob("test_*.py"):
                content = test_file.read_text(encoding="utf-8")
                if contains_forbidden_hypothesis_usage(content):
                    pytest.fail(
                        "Property-based test found in forbidden directory: "
                        f"{test_file.relative_to(ROOT)}"
                    )


@pytest.mark.architecture
class TestLayerTestCoverage:
    """Validate each layer has required test types."""

    def test_unit_tests_exist_per_layer(self) -> None:
        matrix = load_matrix()
        for layer in must_unit_layers(matrix):
            layer_test_dir = TESTS_DIR / "unit" / layer
            if layer_test_dir.is_dir():
                test_files = list(layer_test_dir.rglob("test_*.py"))
                assert test_files, (
                    f"Layer '{layer}' requires unit tests but none found in "
                    f"{layer_test_dir.relative_to(ROOT)}"
                )


@pytest.mark.architecture
class TestCanonicalTestLanes:
    """Validate named test-health lanes stay stable and wrapper-ready."""

    EXPECTED_LANES = {
        "smoke",
        "unit-fast",
        "repo-backed-unit",
        "unit-parallel-safe",
        "integration-replay",
        "security",
        "contracts",
        "architecture",
        "architecture-fast-boundary",
        "architecture-slow-governance",
        "architecture-read-only-audit",
        "e2e",
        "e2e-smoke",
        "e2e-nightly-full",
        "memory",
        "performance",
        "integration-determinism",
        "integration-idempotency",
        "integration-composite-resume",
        "coverage-verify",
    }

    def test_matrix_declares_exact_canonical_test_lanes(self) -> None:
        matrix = load_matrix()
        test_lanes = matrix.get("test_lanes", {})
        lanes = test_lanes.get("lanes", {})
        execution_defaults = test_lanes.get("execution_defaults", {})

        assert test_lanes.get("schema_version") == 1
        assert execution_defaults.get("pythonpath") == "src"
        assert (
            execution_defaults.get("direct_runner")
            == "scripts/engineering/dev/run_pytest.sh"
        )
        assert (
            execution_defaults.get("sharded_runner")
            == "scripts/engineering/dev/run_pytest_sharded.sh"
        )
        assert set(lanes) == self.EXPECTED_LANES

        for lane_name, lane in lanes.items():
            assert lane.get("suite_name") == lane_name
            assert lane.get("description")
            assert lane.get("marker_expression")
            assert lane.get("pytest_args")
            assert lane.get("runner_backend") in {
                "engineering_qa",
                "run_pytest",
                "run_pytest_sharded",
            }
            assert lane.get("runner")
            assert lane.get("coverage_gate") in {"none", "repo-wide"}
            assert lane.get("replay_mode") in {
                "mixed",
                "not_applicable",
                "replay_or_no_api",
                "vcr_none",
                "vcr_replay_only",
            }
            artifacts = lane.get("expected_artifacts", {})
            if lane.get("read_only") is True:
                assert artifacts.get("junit_xml") is False
                assert artifacts.get("json_summary") is False
                assert lane.get("mutates_artifacts") is False
            else:
                assert artifacts.get("junit_xml") is True
                assert artifacts.get("json_summary") is True

    def test_canonical_test_lane_paths_and_runners_exist(self) -> None:
        matrix = load_matrix()
        lanes = matrix["test_lanes"]["lanes"]

        for lane_name, lane in lanes.items():
            runner = lane_runner(lane)
            assert runner.exists(), (
                f"{lane_name} references missing runner: {runner.relative_to(ROOT)}"
            )

            paths = lane_paths(lane)
            assert paths, f"{lane_name} must declare at least one path"
            for path in paths:
                assert path.exists(), (
                    f"{lane_name} references missing test path: "
                    f"{path.relative_to(ROOT)}"
                )

    def test_only_coverage_verify_enforces_repo_wide_coverage(self) -> None:
        matrix = load_matrix()
        lanes = matrix["test_lanes"]["lanes"]

        repo_wide_coverage_lanes = {
            lane_name
            for lane_name, lane in lanes.items()
            if lane.get("coverage_gate") == "repo-wide"
        }
        lanes_with_coverage_args = {
            lane_name
            for lane_name, lane in lanes.items()
            if any(str(arg).startswith("--cov") for arg in lane.get("pytest_args", []))
        }

        assert repo_wide_coverage_lanes == {"coverage-verify"}
        assert lanes_with_coverage_args == {"coverage-verify"}
        assert "--cov-fail-under=85" not in lanes["coverage-verify"]["pytest_args"], (
            "coverage-verify shard lane must not enforce the hard threshold before "
            "combined coverage is computed"
        )

    def test_test_quality_authority_model_is_explicit(self) -> None:
        matrix = load_matrix()
        authority = matrix["test_lanes"].get("authority_model", {})

        assert authority.get("hard_merge_truth") == [
            "live_ci_status",
            "coverage-verify",
        ]
        assert "reports/quality/test-runs/rollup.md" in authority.get(
            "historical_evidence",
            [],
        )
        assert "local_test_health_rollups" in authority.get("advisory_telemetry", [])
        assert "clean src/bioetl tree" in authority.get("dirty_tree_policy", "")

    def test_parallel_execution_policy_keeps_local_pytest_default_serial(self) -> None:
        matrix = load_matrix()
        policy = matrix["test_lanes"].get("parallel_execution_policy", {})
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        pytest_config = pyproject["tool"]["pytest"]["ini_options"]
        addopts = [str(option) for option in pytest_config["addopts"]]
        optional_deps = pyproject["project"]["optional-dependencies"]

        assert policy["local_pytest_default"] == "serial"
        assert policy["forbid_global_xdist_addopts"] is True
        assert "-n" not in addopts
        assert "--numprocesses" not in addopts
        assert any(
            str(requirement).startswith("pytest-xdist")
            for requirement in optional_deps["tests"]
        )
        assert any(
            str(requirement).startswith("pytest-xdist")
            for requirement in optional_deps["dev"]
        )

    def test_parallel_execution_policy_is_limited_to_sharded_lanes(self) -> None:
        matrix = load_matrix()
        test_lanes = matrix["test_lanes"]
        lanes = test_lanes["lanes"]
        policy = test_lanes["parallel_execution_policy"]
        explicit_parallel = set(policy["explicit_parallel_lanes"])
        serial_or_bounded = set(policy["serial_or_bounded_lanes"])

        assert explicit_parallel.isdisjoint(serial_or_bounded)
        assert explicit_parallel | serial_or_bounded == set(lanes)
        for lane_name in explicit_parallel:
            lane = lanes[lane_name]
            assert lane["runner_backend"] == "run_pytest_sharded"
            assert lane["runner"] == "scripts/engineering/dev/run_pytest_sharded.sh"

        assert lanes["integration-replay"]["replay_mode"] == "vcr_replay_only"
        assert "integration-replay" in serial_or_bounded
        assert "VCR-backed replay lanes stay serial" in policy["vcr_parallel_policy"]
        assert "no:xdist" in lanes["performance"]["pytest_args"]
        assert (
            "Benchmark lanes explicitly disable xdist"
            in policy["benchmark_parallel_policy"]
        )

    def test_lane_marker_boundaries_match_current_policy(self) -> None:
        matrix = load_matrix()
        lanes = matrix["test_lanes"]["lanes"]

        assert lanes["smoke"]["marker_expression"] == "not benchmark and not memory"
        assert (
            lanes["unit-fast"]["marker_expression"]
            == "not repo_backed and not slow and not benchmark and not memory"
        )
        assert (
            lanes["repo-backed-unit"]["marker_expression"]
            == "repo_backed and not slow and not benchmark and not memory"
        )
        assert lanes["repo-backed-unit"]["paths"] == ["tests/unit/repo_backed/"]
        assert lanes["unit-parallel-safe"]["runner_backend"] == "run_pytest_sharded"
        assert (
            lanes["unit-parallel-safe"]["marker_expression"]
            == "not repo_backed and not slow and not serial and not benchmark and not memory"
        )
        assert lanes["unit-parallel-safe"]["paths"] == ["tests/unit/"]
        assert "S1-domain-core" in lanes["unit-parallel-safe"]["runner_options"]
        assert "S4-app-services" in lanes["unit-parallel-safe"]["runner_options"]
        assert "S6-crosscutting-unit" in lanes["unit-parallel-safe"]["runner_options"]
        assert lanes["integration-replay"]["replay_mode"] == "vcr_replay_only"
        assert "--vcr-record=none" in lanes["integration-replay"]["pytest_args"]
        assert (
            lanes["security"]["marker_expression"]
            == "security and not benchmark and not memory"
        )
        assert lanes["integration-determinism"]["marker_expression"] == (
            "integration and not slow and not benchmark and not memory"
        )
        assert lanes["integration-idempotency"]["marker_expression"] == (
            "integration and not slow and not benchmark and not memory"
        )
        assert lanes["integration-composite-resume"]["marker_expression"] == (
            "integration and not slow and not benchmark and not memory"
        )
        assert lanes["architecture"]["runner_backend"] == "run_pytest_sharded"
        assert (
            "S7-architecture-fast-boundary" in lanes["architecture"]["runner_options"]
        )
        assert (
            "S7-architecture-slow-governance" in lanes["architecture"]["runner_options"]
        )
        assert lanes["architecture-fast-boundary"]["runner_backend"] == (
            "run_pytest_sharded"
        )
        assert lanes["architecture-fast-boundary"]["runner_options"] == [
            "--shard",
            "S7-architecture-fast-boundary",
        ]
        assert lanes["architecture-slow-governance"]["runner_backend"] == (
            "run_pytest_sharded"
        )
        assert lanes["architecture-slow-governance"]["runner_options"] == [
            "--shard",
            "S7-architecture-slow-governance",
        ]
        assert lanes["architecture-read-only-audit"]["runner_backend"] == (
            "engineering_qa"
        )
        assert lanes["architecture-read-only-audit"]["read_only"] is True
        assert lanes["architecture-read-only-audit"]["mutates_artifacts"] is False
        assert lanes["architecture-read-only-audit"]["runner"] == (
            "scripts/engineering/qa/run_architecture_audit_read_only.py"
        )
        assert (
            lanes["e2e"]["marker_expression"] == "e2e and not benchmark and not memory"
        )
        assert lanes["e2e-smoke"]["paths"] == [
            "tests/e2e/test_chembl_activity_e2e.py",
            "tests/e2e/test_pipeline_matrix_e2e.py",
        ]
        assert (
            lanes["e2e-smoke"]["marker_expression"]
            == "e2e_smoke and not benchmark and not memory"
        )
        assert lanes["e2e-smoke"]["replay_mode"] == "vcr_none"
        assert lanes["e2e-nightly-full"]["paths"] == ["tests/e2e/"]
        assert lanes["e2e-nightly-full"]["marker_expression"] == (
            "e2e and not e2e_smoke and not benchmark and not memory"
        )
        assert lanes["memory"]["marker_expression"] == "memory and not benchmark"
        assert lanes["memory"]["paths"] == [
            "tests/smoke/test_neo4j_memory_mcp_smoke.py"
        ]
        assert lanes["performance"]["marker_expression"] == "benchmark and performance"
        assert "-p" in lanes["performance"]["pytest_args"]
        assert "no:xdist" in lanes["performance"]["pytest_args"]
        assert lanes["coverage-verify"]["runner_backend"] == "run_pytest_sharded"
        assert "--keep-coverage-files" in lanes["coverage-verify"]["runner_options"]
        assert (
            lanes["coverage-verify"]["marker_expression"]
            == "not e2e and not benchmark and not memory"
        )

    def test_test_health_confidence_policy_tracks_not_run_lane_assertions(self) -> None:
        matrix = load_matrix()
        confidence = matrix.get("test_health_confidence", {})
        entries = confidence.get("lane_absence_skip_classes", [])

        assert isinstance(entries, list)
        assert entries == [
            {
                "lane": "contracts",
                "skip_class": "contract_lane_not_run",
                "reason": (
                    "Current quality-gate run does not execute the canonical "
                    "contracts lane."
                ),
            },
            {
                "lane": "e2e",
                "skip_class": "e2e_lane_not_run",
                "reason": (
                    "Current quality-gate run does not execute the canonical e2e lane."
                ),
            },
            {
                "lane": "memory",
                "skip_class": "memory_lane_not_run",
                "reason": (
                    "Current quality-integral gate slice runs architecture "
                    "checks only; the dedicated CI memory-tests lane remains "
                    "separate and is not represented in this local classification."
                ),
            },
        ]
