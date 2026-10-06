"""Transported CI evidence must be complete and must never execute checks on reuse."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from scripts.engineering.ci import proof_closeout_runner as runner

pytestmark = pytest.mark.unit


def test_receive_keeps_classifier_files_outside_checkout(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "pr-gate-decisions.json").write_text("{}")
    proof = workspace / "reports/quality/proof-or-stop/shared/architecture"
    proof.mkdir(parents=True)
    (proof / "producer.log").write_text("passed")
    destination = tmp_path / "checkout/reports/quality/proof-or-stop/shared"
    monkeypatch.setattr(runner, "EVIDENCE", destination)
    runner.receive(workspace)
    assert (destination / "architecture/producer.log").read_text() == "passed"
    assert not (tmp_path / "checkout/pr-gate-decisions.json").exists()
    with pytest.raises(FileExistsError):
        runner.receive(workspace)


@pytest.fixture()
def evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "EVIDENCE", tmp_path / "evidence")
    plan = {
        "task_id": "task",
        "claim": "tested",
        "checks": {"example": {"argv": [sys.executable, "-c", "print('measured')"]}},
    }
    monkeypatch.setattr(runner, "catalog", lambda: plan)
    monkeypatch.setattr(runner, "ci_identity", lambda: "workflow:1")
    source = {"head_sha": "a" * 40}
    repository = {"ci_run_id": "workflow:1"}
    monkeypatch.setattr(
        runner, "discover_context", lambda *a, **kw: (repository, source.copy())
    )
    monkeypatch.setenv("CIRCLE_BUILD_URL", "https://circleci.com/gh/example/repo/1")
    monkeypatch.setenv("CIRCLE_BUILD_NUM", "1")
    return plan, source


def test_real_producer_runs_once_and_reuse_only_reads(evidence, monkeypatch):
    _, source = evidence
    assert runner.produce("example") == 0

    def forbidden(*a, **kw):
        pytest.fail("Validation must not launch a producer")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    record = runner.validate_execution("example", "workflow:1", source)
    assert record["exit_code"] == 0
    assert (runner.EVIDENCE / "example/producer.log").read_text().strip() == "measured"


def test_failed_producer_is_recorded_and_cannot_be_reused(evidence):
    plan, source = evidence
    plan["checks"]["example"]["argv"] = [sys.executable, "-c", "raise SystemExit(7)"]
    assert runner.produce("example") == 7
    with pytest.raises(ValueError, match="Incomplete or foreign"):
        runner.validate_execution("example", "workflow:1", source)


@pytest.mark.parametrize(
    "damage", ["log", "missing", "workflow", "sha", "command", "catalog"]
)
def test_reuse_rejects_damaged_or_foreign_evidence(evidence, damage):
    plan, source = evidence
    assert runner.produce("example") == 0
    folder = runner.EVIDENCE / "example"
    if damage == "log":
        (folder / "producer.log").write_text("substituted")
    elif damage == "missing":
        (folder / "producer.log").unlink()
    elif damage == "workflow":
        source = source.copy()
    elif damage == "sha":
        source = {"head_sha": "b" * 40}
    elif damage == "command":
        record_path = folder / "execution.json"
        record = json.loads(record_path.read_text())
        record["argv"] = ["true"]
        runner.write_json(record_path, record)
    else:
        plan["claim"] = "done"
    with pytest.raises(ValueError):
        runner.validate_execution(
            "example", "other" if damage == "workflow" else "workflow:1", source
        )


def test_assembly_rejects_missing_producer_without_running_it(evidence, monkeypatch):
    monkeypatch.setattr(
        runner.subprocess, "Popen", lambda *a, **kw: pytest.fail("Unexpected execution")
    )
    assert runner.main(["assemble"]) == 2


def test_secrets_are_redacted_before_artifact_digests(evidence, monkeypatch):
    plan, source = evidence
    monkeypatch.setenv("EXAMPLE_API_KEY", "sample-sensitive-test-value")
    plan["checks"]["example"]["argv"] = [
        sys.executable,
        "-c",
        "import os; print(os.environ['EXAMPLE_API_KEY'])",
    ]
    assert runner.produce("example") == 0
    assert (
        "sample-sensitive-test-value"
        not in (runner.EVIDENCE / "example/producer.log").read_text()
    )
    runner.validate_execution("example", "workflow:1", source)


def test_quality_requires_architecture_evidence_before_launch(evidence, monkeypatch):
    plan, _ = evidence
    plan["checks"]["quality"] = plan["checks"]["example"]
    checked = []

    def validate(name, *args):
        checked.append(name)
        if name == "architecture":
            raise ValueError("Missing architecture evidence")

    monkeypatch.setattr(runner, "validate_execution", validate)
    monkeypatch.setattr(
        runner.subprocess, "Popen", lambda *a, **kw: pytest.fail("Unexpected execution")
    )
    with pytest.raises(ValueError, match="Missing architecture"):
        runner.produce("quality")
    assert checked == ["coverage", "architecture"]
