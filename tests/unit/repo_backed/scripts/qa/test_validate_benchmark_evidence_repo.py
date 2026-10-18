"""Repo-backed contract tests for the benchmark evidence validation gates."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.repo_backed


def test_benchmark_evidence_workflow_keeps_validator_and_main_gates_independent():
    root = Path(__file__).resolve().parents[5]
    workflow = yaml.safe_load(
        (root / ".github/workflows/performance-nightly.yml").read_text()
    )
    steps = {
        step["name"]: step
        for step in workflow["jobs"]["performance-regression-gate"]["steps"]
    }
    producer = steps["Run all performance benchmarks"]
    validation = steps["Validate benchmark evidence"]
    assert producer["id"] == "benchmarks"
    assert "continue-on-error" not in producer
    assert (
        "python -m scripts.engineering.qa validate-benchmark-evidence"
        in validation["run"]
    )
    assert validation["env"]["PRODUCER_OUTCOME"] == "${{ steps.benchmarks.outcome }}"
    assert '--producer-outcome "$PRODUCER_OUTCOME"' in validation["run"]
    assert "benchmark-validation-manifest.json" in validation["run"]
    assert "gate-hotspot-report" in steps["Gate on degradation report"]["run"]
    assert "if [ -f" not in steps["Build hotspot degradation report"]["run"]
    assert (
        "steps.validate-evidence.outcome == 'success'"
        in steps["Reduce benchmark evidence"]["if"]
    )
    assert "reduce-benchmark-evidence" in steps["Reduce benchmark evidence"]["run"]
    assert (
        "test -s reports/performance/benchmark-validation-manifest.json"
        in steps["Require validated benchmark artifacts"]["run"]
    )


def test_benchmark_evidence_validator_tests_are_collected_by_automatic_lanes():
    root = Path(__file__).resolve().parents[5]
    workflow = (root / ".github/workflows/tests.yml").read_text()
    assert "repo-backed-unit" in workflow
    assert "tests/unit/repo_backed/" in workflow
    assert "tests/unit/scripts/" in workflow
    assert (
        Path(__file__)
        .relative_to(root)
        .as_posix()
        .startswith("tests/unit/repo_backed/")
    )
    assert (
        root / "tests/unit/scripts/qa/test_validate_benchmark_evidence.py"
    ).is_file()


def test_nightly_caller_declares_dataset_and_loads_guard_before_benchmark():
    root = Path(__file__).resolve().parents[5]
    workflow = yaml.safe_load(
        (root / ".github/workflows/performance-nightly.yml").read_text()
    )
    steps = (
        workflow["jobs"]["performance"]["steps"]
        if "performance" in workflow["jobs"]
        else next(iter(workflow["jobs"].values()))["steps"]
    )
    producer = next(step for step in steps if step.get("id") == "benchmarks")
    assert (
        producer["env"]["BIOETL_BENCHMARK_DATASET"] == "bioetl-synthetic-performance-v1"
    )
    assert producer["run"].index("-p tests.benchmarks.benchmark_vcs_guard") < producer[
        "run"
    ].index("-p benchmark")
