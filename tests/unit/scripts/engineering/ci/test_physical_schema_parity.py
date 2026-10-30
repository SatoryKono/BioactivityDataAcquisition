"""Fail-closed selection, execution evidence, and canonical parity routing."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest
import yaml

from scripts.engineering.ci import physical_schema_parity as parity
from scripts.engineering.ci.pr_gate import classify_changes, load_catalog
from scripts.engineering.ci.pr_lane_results import assert_step_outcomes, build_results

pytestmark = pytest.mark.unit


def _junit(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "parity.xml"
    path.write_text(f"<testsuites><testsuite>{body}</testsuite></testsuites>")
    return path


def test_complete_passing_inventory_is_accepted(tmp_path: Path) -> None:
    body = "".join(
        f'<testcase classname="{target[:-3].replace("/", ".")}" name="control"/>'
        for target in parity.TARGETS
    )
    assert parity.validate_junit(_junit(tmp_path, body)) == []


@pytest.mark.parametrize("tag", ["failure", "error", "skipped"])
def test_unsuccessful_evidence_is_rejected(tmp_path: Path, tag: str) -> None:
    path = _junit(tmp_path, f'<testcase classname="synthetic"><{tag}/></testcase>')
    assert any(tag in error for error in parity.validate_junit(path))


def test_missing_empty_and_partial_results_are_rejected(tmp_path: Path) -> None:
    assert parity.validate_junit(tmp_path / "absent.xml") == ["missing parity JUnit"]
    empty = _junit(tmp_path, "")
    assert "empty parity JUnit" in parity.validate_junit(empty)
    assert parity.validate_junit(empty, ()) == ["empty parity selection"]
    partial = _junit(tmp_path, '<testcase classname="other" name="passing"/>')
    assert all(
        "missing parity module" in error for error in parity.validate_junit(partial)
    )


def test_missing_backend_is_not_a_skip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(parity.importlib.util, "find_spec", lambda name: None)
    assert parity.main(["--junit", str(tmp_path / "result.xml")]) == 2
    assert not (tmp_path / "result.xml").exists()


@pytest.mark.parametrize(
    "code,tag,expected", [(1, "", 1), (0, "<skipped/>", 1), (0, "", 0)]
)
def test_child_exit_and_evidence_both_gate_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    code: int,
    tag: str,
    expected: int,
) -> None:
    result_path = tmp_path / "child.xml"
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k nonexistent -m not_integration")
    monkeypatch.setenv(parity.NEGATIVE_CONTROL_ENV, "ambient-ignored")

    def child(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == parity.REPO_ROOT
        assert "--strict-markers" in command
        assert "--strict-config" in command
        assert "--import-mode=importlib" in command
        assert command[3 : 3 + len(parity.TARGETS)] == list(parity.TARGETS)
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "PYTEST_ADDOPTS" not in env
        assert env[parity.NEGATIVE_CONTROL_ENV] == "1"
        body = "".join(
            f'<testcase classname="{target[:-3].replace("/", ".")}" name="control">{tag}</testcase>'
            for target in parity.TARGETS
        )
        result_path.write_text(
            f"<testsuites><testsuite>{body}</testsuite></testsuites>"
        )
        return subprocess.CompletedProcess(command, code)

    monkeypatch.setattr(parity.subprocess, "run", child)
    assert parity.main(["--junit", str(result_path), "--negative-control"]) == expected


def test_stale_or_malformed_evidence_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "stale.xml"
    path.write_text("<not valid XML")
    assert "unreadable parity JUnit" in parity.validate_junit(path)[0]
    assert parity.main(["--junit", str(path)]) == 2
    assert path.read_text() == "<not valid XML"


def test_missing_or_empty_selection_fails_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for targets in ((), ("tests/missing_parity_module.py",)):
        monkeypatch.setattr(parity, "TARGETS", targets)
        assert parity.main(["--junit", str(tmp_path / "result.xml")]) == 2
    assert not (tmp_path / "result.xml").exists()


@pytest.mark.parametrize("outcome", ["failure", "skipped", "", "cancelled"])
def test_schema_mismatch_or_missing_step_fails_required_gate(outcome: str) -> None:
    decisions = {
        "generated-artifacts": {"decision": "required", "reason": "path_match"}
    }
    errors = assert_step_outcomes(
        decisions,
        {"schema-artifacts": "success", "schema-parity": outcome},
        owner="class-lane",
    )
    assert errors
    results = build_results(decisions, {"class-lane": "failure"}, head_sha="a" * 40)
    assert results["generated-artifacts"]["required"] == "failure"


@pytest.mark.parametrize(
    "path",
    [
        "src/bioetl/infrastructure/storage/silver/schema_drift_operations.py",
        "src/bioetl/infrastructure/storage/gold_writer.py",
        "configs/base/pipeline.yaml",
        "configs/providers/chembl.yaml",
        "configs/entities/chembl/activity.yaml",
        "pyproject.toml",
        "uv.lock",
        *parity.TARGETS,
        "scripts/engineering/ci/physical_schema_parity.py",
    ],
)
def test_all_backend_inputs_select_canonical_gate(path: str) -> None:
    catalog = load_catalog(
        parity.REPO_ROOT / "configs/quality/github_required_checks.yaml"
    )
    matrix = classify_changes(catalog, [path], head_sha="a" * 40)
    assert matrix["decisions"]["generated-artifacts"]["decision"] == "required"


def test_one_canonical_schema_step_runs_real_matrix_and_retains_aggregation() -> None:
    workflow = yaml.safe_load(
        (parity.REPO_ROOT / ".github/workflows/pr-required.yml").read_text()
    )
    steps = workflow["jobs"]["class-lane"]["steps"]
    parity_steps = [step for step in steps if step.get("id") == "schema-parity"]
    assert len(parity_steps) == 1
    step = parity_steps[0]
    assert "scripts.engineering.ci.physical_schema_parity" in step["run"]
    assert "set -euo pipefail" in step["run"]
    assert "continue-on-error" not in step
    assert any("steps.schema-parity.outcome" in step.get("run", "") for step in steps)
