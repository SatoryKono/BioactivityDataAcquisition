"""Architecture tests for CI pytest execution strategy."""

from __future__ import annotations

from pathlib import Path


def _read_workflow(path: str) -> str:
    """Read workflow content as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def test_coverage_job_uses_resilient_pytest_runner() -> None:
    """Coverage workflow must use resilient runner with crash fallback."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "scripts/ci/run_pytest_resilient.py" in workflow, (
        "tests workflow must run resilient pytest runner in coverage-verify job"
    )
    assert "--parallel-marker \"not e2e and not benchmark and not serial\"" in workflow
    assert "--serial-marker \"serial and not e2e and not benchmark\"" in workflow


def test_parallel_ci_jobs_exclude_serial_marker() -> None:
    """Parallel CI jobs should not execute serial-only tests."""
    workflow = _read_workflow(".github/workflows/tests.yml")
    assert "-m \"not slow and not serial\"" in workflow, (
        "test-fast job must exclude serial marker in parallel mode"
    )
    assert "-m \"not serial\"" in workflow, (
        "test-matrix job must exclude serial marker in parallel mode"
    )
