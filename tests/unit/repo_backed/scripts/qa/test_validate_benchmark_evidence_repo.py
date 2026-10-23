"""Repo-backed contract tests for the benchmark evidence validation gates."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

_MEASURED_SHA = "a" * 40
_RAW_SHA = "b" * 64

pytestmark = pytest.mark.repo_backed


def test_benchmark_evidence_workflow_keeps_validator_and_main_gates_independent():
    """Pass the validation manifest through while keeping the two gates independent."""
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


def _assert_receipt_parents_and_index(root: Path, evidence: str, receipt: str) -> None:
    """Parents stay un-ignored and git add tracks the receipt without -f."""
    path = root / receipt
    index_dir = Path(tempfile.mkdtemp(prefix="benchmark-receipt-index-"))
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = str(index_dir / "index")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        parents = (
            "reports/performance",
            "reports/performance/evidence",
            f"reports/performance/evidence/{_MEASURED_SHA}",
            evidence,
        )
        for relative in parents:
            assert _git_check_ignore(root, relative, verbose=False).returncode == 1, (
                relative
            )
            assert _ignore_pattern(root, relative).startswith("!"), relative
        added = subprocess.run(
            ["git", "add", "--", receipt],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert added.returncode == 0, added.stderr
        listed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", receipt],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert listed.returncode == 0, listed.stderr
        assert listed.stdout.strip() == receipt
    finally:
        path.unlink(missing_ok=True)
        shutil.rmtree(index_dir, ignore_errors=True)
        folder = path.parent
        while folder != root / "reports" / "performance" / "evidence":
            try:
                folder.rmdir()
            except OSError:
                break
            folder = folder.parent


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
        f"{evidence}/benchmark-validation-manifest.json",
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
    receipt = f"{evidence}/benchmark-validation-manifest.json"
    assert _ignore_pattern(root, receipt) == (
        "!/reports/performance/evidence/*/*/benchmark-validation-manifest.json"
    )
    _assert_receipt_parents_and_index(root, evidence, receipt)


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


def _candidate_for_adopted_summary(
    evidence_root: Path, summary: dict[str, object]
) -> tuple[Path, dict[str, object]]:
    """Select the capture named by the accepted summary, ignoring other captures."""
    baseline_sha = summary["baseline_sha"]
    raw_sha256 = summary["raw_sha256"]
    matches: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(evidence_root.rglob("benchmark-summary-candidate.json")):
        candidate = json.loads(path.read_text(encoding="utf-8"))
        if (
            candidate.get("baseline_sha") == baseline_sha
            and candidate.get("raw_sha256") == raw_sha256
        ):
            matches.append((path, candidate))
    assert len(matches) == 1
    return matches[0]


def test_reviewed_summary_adopts_candidate_without_changing_measurements():
    """Flip only adoption; keep the failed gate and the measured bytes."""
    root = Path(__file__).resolve().parents[5]
    summary = json.loads(
        (root / "reports/performance/benchmark-summary.json").read_text(
            encoding="utf-8"
        )
    )
    candidate_path, candidate = _candidate_for_adopted_summary(
        root / "reports/performance/evidence", summary
    )
    folder = candidate_path.parent
    assert candidate["adoption"] == "proposed"
    adopted = dict(candidate)
    adopted["adoption"] = "measured"
    assert summary == adopted
    raw = (folder / "benchmark-measurements.json").read_bytes()
    receipt = (folder / "benchmark-validation-manifest.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == summary["raw_sha256"]
    assert hashlib.sha256(receipt).hexdigest() == summary["validation_manifest_sha256"]
    gate = json.loads((folder / "benchmark-gate.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (folder / "benchmark-manifest.json").read_text(encoding="utf-8")
    )
    assert gate == manifest
    assert gate["status"] == "failed"
    assert gate["reason"] == "insufficient_baseline"
    assert gate["measured_sha"] == summary["baseline_sha"]
    assert gate["raw_sha256"] == summary["raw_sha256"]


def test_additional_capture_does_not_replace_the_adopted_baseline(
    tmp_path: Path,
) -> None:
    """A later capture stays unselected when the summary names another raw digest."""
    adopted_sha = "a" * 40
    adopted_raw = "b" * 64
    other_sha = "c" * 40
    other_raw = "d" * 64
    evidence = tmp_path / "evidence"

    def write_capture(measured_sha: str, raw_sha256: str, mean: str) -> None:
        folder = evidence / measured_sha / raw_sha256
        folder.mkdir(parents=True)
        candidate = {
            "adoption": "proposed",
            "baseline_sha": measured_sha,
            "dataset": "bioetl-synthetic-benchmarks-v1",
            "environment": "github-actions",
            "raw_sha256": raw_sha256,
            "schema_version": 1,
            "scopes": ["tests/benchmarks/"],
            "tests": [
                {
                    "dataset": "bioetl-synthetic-benchmarks-v1",
                    "environment": "github-actions",
                    "mean": mean,
                    "scope": "tests/benchmarks/",
                    "test_id": "tests/benchmarks/test_performance.py::example",
                }
            ],
            "threshold": "0.1",
        }
        (folder / "benchmark-summary-candidate.json").write_text(
            json.dumps(candidate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    write_capture(adopted_sha, adopted_raw, "1.0")
    write_capture(other_sha, other_raw, "999")
    summary = json.loads(
        (
            evidence / adopted_sha / adopted_raw / "benchmark-summary-candidate.json"
        ).read_text(encoding="utf-8")
    )
    summary["adoption"] = "measured"
    selected_path, selected = _candidate_for_adopted_summary(evidence, summary)
    assert selected_path.parent.name == adopted_raw
    assert selected["baseline_sha"] == adopted_sha
    assert selected["raw_sha256"] == adopted_raw
    assert selected["tests"][0]["mean"] == "1.0"
    adopted = dict(selected)
    adopted["adoption"] = "measured"
    assert summary == adopted
