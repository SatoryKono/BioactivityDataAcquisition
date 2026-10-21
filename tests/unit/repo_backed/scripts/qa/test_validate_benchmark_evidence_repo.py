"""Repo-backed contract tests for the benchmark evidence validation gates."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

_MEASURED_SHA = "a" * 40
_RAW_SHA = "b" * 64

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
    producer = steps["Run pytest-benchmark cases"]
    validation = steps["Validate benchmark evidence"]
    contract = steps["Require pytest-benchmark measurement JSON"]
    assert contract["id"] == "measurement-contract"
    assert (
        validation["env"]["CONTRACT_OUTCOME"]
        == "${{ steps.measurement-contract.outcome }}"
    )
    assert '--contract-outcome "$CONTRACT_OUTCOME"' in validation["run"]
    assert (
        "--failure-gate-out reports/performance/benchmark-gate.json"
        in validation["run"]
    )
    assert (
        "steps.measurement-contract.outcome == 'success'"
        in steps["Reduce benchmark evidence"]["if"]
    )
    assert (
        'test "$CONTRACT_OUTCOME" = success'
        in steps["Require validated benchmark artifacts"]["run"]
    )
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
        "--validation-manifest reports/performance/benchmark-validation-manifest.json"
        in steps["Reduce benchmark evidence"]["run"]
    )
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


def _git_check_ignore(
    root: Path, relative: str, *, verbose: bool
) -> subprocess.CompletedProcess[str]:
    command = ["git", "check-ignore", "--no-index", "--", relative]
    if verbose:
        command.insert(2, "-v")
    else:
        command.insert(2, "-q")
    return subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def _ignore_pattern(root: Path, relative: str) -> str:
    completed = _git_check_ignore(root, relative, verbose=True)
    assert completed.returncode == 0, completed.stderr
    pattern, _pathname = completed.stdout.rstrip("\n").split("\t", 1)
    return pattern.rsplit(":", 1)[-1]


def test_root_benchmark_manifest_stays_ignored_while_evidence_copy_is_tracked():
    root = Path(__file__).resolve().parents[5]
    evidence = f"reports/performance/evidence/{_MEASURED_SHA}/{_RAW_SHA}"
    ignored = (
        "reports/performance/benchmark-manifest.json",
        "reports/performance/benchmark-measurements.json",
        "reports/performance/benchmark-gate.json",
        "reports/performance/benchmark-validation-manifest.json",
        f"{evidence}/notes.txt",
    )
    tracked = (
        "reports/performance/benchmark-summary.json",
        f"{evidence}/benchmark-manifest.json",
        f"{evidence}/benchmark-measurements.json",
        f"{evidence}/benchmark-gate.json",
        f"{evidence}/benchmark-summary-candidate.json",
    )
    for relative in ignored:
        assert _git_check_ignore(root, relative, verbose=False).returncode == 0, (
            relative
        )
    for relative in tracked:
        assert _git_check_ignore(root, relative, verbose=False).returncode == 1, (
            relative
        )
    assert _ignore_pattern(root, "reports/performance/benchmark-manifest.json") == (
        "/reports/performance/*"
    )
    assert _ignore_pattern(root, f"{evidence}/benchmark-manifest.json") == (
        "!/reports/performance/evidence/*/*/benchmark-manifest.json"
    )


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
    assert "BIOETL_BENCHMARK_DATASET=bioetl-synthetic-benchmarks-v1" in producer["run"]
    command = "\n".join(
        line
        for line in producer["run"].splitlines()
        if not line.lstrip().startswith("#")
    )
    assert command.index("-p tests.benchmarks.benchmark_vcs_guard") < command.index(
        "-p benchmark"
    )
