from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts.ops.runtime.docker import runtime_manager

pytestmark = pytest.mark.repo_backed


def _spec() -> runtime_manager.StackSpec:
    return runtime_manager.StackSpec(
        name="main",
        project="bioetl-main",
        compose_file=Path("docker-compose.yml"),
        required_services=("bioetl",),
        expected_images={"bioetl": "bioetl:test@sha256:expected"},
    )


def test_readiness_fails_on_restart_oom_and_image_drift() -> None:
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=1,
        oom_killed=True,
        image="bioetl:test@sha256:actual",
    )

    findings = runtime_manager.readiness_findings(_spec(), [snapshot], baseline={})

    assert {finding["cause"] for finding in findings} == {
        "oom_killed",
        "unexpected_restart",
        "image_identity_drift",
    }


def test_running_without_health_is_not_ready() -> None:
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="none",
        restart_count=0,
        oom_killed=False,
        image="bioetl:test@sha256:expected",
    )

    assert runtime_manager.readiness_findings(_spec(), [snapshot]) == [
        {
            "cause": "service_unready",
            "service": "bioetl",
            "state": "running",
            "health": "none",
        }
    ]


def test_preflight_failure_writes_one_redacted_incident_without_mutation(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        calls.append(list(command))
        return runtime_manager.CommandResult(
            list(command), 2, stderr="token=ghp_abcdefghijklmnop"
        )

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=False,
        runner=runner,
        sleep=lambda _seconds: None,
    )

    assert result == 1
    assert len(calls) == 1
    assert "compose" not in calls[0]
    incidents = list(tmp_path.glob("docker-incident-*.json"))
    assert len(incidents) == 1
    payload = json.loads(incidents[0].read_text(encoding="utf-8"))
    assert payload["primary_cause"] == "preflight_failed"
    assert "ghp_" not in incidents[0].read_text(encoding="utf-8")


def test_recovery_is_bounded_to_three_attempts_and_writes_one_incident(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        if "docker_runtime_preflight.py" in " ".join(current):
            return runtime_manager.CommandResult(current, 0)
        if current[-2:] == ["--format", "json"]:
            return runtime_manager.CommandResult(current, 0, stdout="[]")
        if "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "up" in current:
            return runtime_manager.CommandResult(current, 1, stderr="unready")
        if "logs" in current:
            return runtime_manager.CommandResult(current, 0, stdout="bounded logs")
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        max_attempts=3,
        sleep=lambda _seconds: None,
    )

    assert result == 1
    assert sum("up" in call for call in calls) == 3
    assert len(list(tmp_path.glob("docker-incident-*.json"))) == 1
    incident = json.loads(
        next(tmp_path.glob("docker-incident-*.json")).read_text(encoding="utf-8")
    )
    assert incident["config_origin"] == "docker-compose.yml"
    assert incident["recent_logs"]["captured"] is True
    assert len(incident["recovery_history"]) == 3


def test_clean_requires_confirmation_and_never_deletes_data(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        calls.append(list(command))
        return runtime_manager.CommandResult(list(command), 0)

    assert (
        runtime_manager.main(["clean", "--report-dir", str(tmp_path)], runner=runner)
        == 2
    )
    assert calls == []
    assert (
        runtime_manager.main(
            [
                "clean",
                "--report-dir",
                str(tmp_path),
                "--confirm-destructive",
                "CLEAN",
            ],
            runner=runner,
        )
        == 0
    )
    rendered = " ".join(calls[-1])
    assert "--volumes" not in rendered
    assert "-v" not in calls[-1]
    assert "prune" not in rendered


def test_recovery_attempts_share_one_overall_deadline(tmp_path: Path) -> None:
    now = [0.0]
    up_calls = 0

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        nonlocal up_calls
        current = list(command)
        if "docker_runtime_preflight.py" in " ".join(current) or "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if current[-2:] == ["--format", "json"]:
            return runtime_manager.CommandResult(current, 0, stdout="[]")
        if "up" in current:
            up_calls += 1
            now[0] += timeout
            return runtime_manager.CommandResult(current, 1, stderr="timeout")
        if "logs" in current:
            return runtime_manager.CommandResult(current, 0)
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        timeout=10,
        max_attempts=3,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )

    assert result == 1
    assert up_calls == 1
    incident = json.loads(
        next(tmp_path.glob("docker-incident-*.json")).read_text(encoding="utf-8")
    )
    assert incident["elapsed_seconds"] <= 10
