"""Architecture tests for CI pytest execution strategy."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def _read_workflow(path: str) -> str:
    """Read workflow content as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def test_coverage_job_combines_shard_coverage_and_runs_serial_pass() -> None:
    """Coverage workflow should combine shard coverage and run serial tests only once."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert (
        "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c" in workflow
    ), "coverage-verify job must download coverage shard artifacts"
    assert "pattern: coverage-data-*" in workflow, (
        "coverage-verify job must download all coverage shard artifacts"
    )
    assert (
        '--parallel-marker "serial and not e2e and not benchmark and not memory"'
        in workflow
    ), "coverage-verify job must run only serial-marker tests directly"
    assert "coverage combine reports/coverage" in workflow, (
        "coverage-verify job must combine shard coverage instead of rerunning the full suite"
    )
    assert "coverage report --show-missing --fail-under=85" in workflow, (
        "coverage-verify job must enforce the 85% threshold on combined coverage"
    )


def test_parallel_ci_jobs_exclude_serial_marker() -> None:
    """Parallel CI jobs should not execute serial-only tests."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert '-m "not slow and not serial and not memory"' in workflow, (
        "test-fast job must exclude serial and memory markers in parallel mode"
    )
    assert '-m "not serial and not memory"' in workflow, (
        "test-matrix job must exclude serial and memory markers in parallel mode"
    )
    assert "--max-worker-restart=0" in workflow, (
        "parallel CI jobs must fail fast on worker restart loops"
    )
    assert "--junitxml=reports/test-telemetry/junit-fast.xml" in workflow, (
        "test-fast job should emit JUnit telemetry for slow-test duration analysis"
    )
    assert "pattern: test-telemetry-*" in workflow, (
        "duration telemetry job must download JUnit telemetry artifacts"
    )


def test_tests_workflow_splits_heavy_preflight_from_dependency_smoke() -> None:
    """Fast test lanes should be gated only by minimal dependency smoke."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "governance-preflight:" in workflow, (
        "tests workflow should keep governance checks in a dedicated preflight job"
    )
    assert "config-schema-preflight:" in workflow, (
        "tests workflow should keep config/schema checks in a dedicated preflight job"
    )
    assert "needs: governance-preflight" in workflow, (
        "quality-metrics-gate should depend on governance-preflight"
    )
    assert 'uv run pytest tests/smoke/ -m "not memory" -v --tb=short' in workflow, (
        "smoke-check must exclude dedicated memory-marked smoke tests"
    )


def test_tests_workflow_publishes_duration_telemetry_artifact() -> None:
    """Tests workflow should publish a stable slow-test telemetry artifact."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "duration-telemetry:" in workflow, (
        "tests workflow should include a dedicated duration-telemetry job"
    )
    assert "test-duration-telemetry" in workflow, (
        "duration-telemetry job should upload a named telemetry artifact"
    )
    assert "slowest-tests.md" in workflow and "slowest-tests.json" in workflow, (
        "duration telemetry output should include both markdown and JSON summaries"
    )


def test_tests_workflow_publishes_test_health_telemetry_artifact() -> None:
    """Tests workflow should fold JUnit telemetry into test-health summaries."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "duration-telemetry:\n        if: always()" in workflow, (
        "duration-telemetry must run even when upstream test jobs fail"
    )
    assert "continue-on-error: true" in workflow, (
        "duration-telemetry should still publish an empty rollup when no telemetry "
        "artifacts are available"
    )
    assert "unit_junit=()" in workflow, (
        "duration-telemetry must not pass missing literal JUnit paths to the aggregator"
    )
    assert "summarize-junit" in workflow, (
        "duration telemetry job should convert existing JUnit XML into test-health JSON"
    )
    assert "--suite security" in workflow, (
        "security matrix telemetry should be represented in test-health summaries"
    )
    assert "--suite memory" in workflow, (
        "memory lane telemetry should be represented in test-health summaries"
    )
    assert "--suite track-d" in workflow, (
        "Track D telemetry should be represented in test-health summaries"
    )
    assert "--github-step-summary" in workflow, (
        "test-health rollup should publish Markdown into the GitHub job summary"
    )
    assert "test-health-telemetry" in workflow, (
        "tests workflow should upload the test-health run history artifact"
    )
    assert "reports/quality/test-runs/" in workflow, (
        "test-health artifacts should be routed under reports/quality/test-runs"
    )


def test_tests_workflow_has_dedicated_memory_lane_outside_coverage() -> None:
    """Neo4j memory tests should run in their own non-coverage lane."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "memory-tests:" in workflow, (
        "tests workflow should define a dedicated memory-tests job"
    )
    assert "--junitxml=reports/test-telemetry/junit-memory.xml" in workflow, (
        "memory-tests job should emit its own telemetry artifact"
    )
    assert ' -m "memory" \\' in workflow or '-m "memory"' in workflow, (
        "memory-tests job must run only the dedicated memory-marked suite"
    )


def test_tests_workflow_has_dedicated_contract_confidence_lane_outside_coverage() -> (
    None
):
    """Offline contract confidence should block independently from coverage."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "contract-confidence:" in workflow, (
        "tests workflow should define a blocking offline contract-confidence job"
    )
    assert "tests/contract/ tests/unit/contracts/" in workflow, (
        "contract-confidence must run the canonical contract surfaces"
    )
    assert '-m "no_api or not network"' in workflow, (
        "contract-confidence must avoid live network contract tests"
    )
    assert (
        "--junitxml=reports/test-telemetry/junit-contract-confidence.xml" in workflow
    ), "contract-confidence must emit JUnit telemetry"
    assert "test-telemetry-contract-confidence" in workflow, (
        "contract-confidence telemetry should be uploaded for test-health rollups"
    )
