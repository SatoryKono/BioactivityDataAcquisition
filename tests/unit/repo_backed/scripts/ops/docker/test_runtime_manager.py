from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from scripts.ops.runtime.docker import runtime_manager

pytestmark = pytest.mark.repo_backed


def _spec(
    *, expected_images: dict[str, str] | None = None
) -> runtime_manager.StackSpec:
    return runtime_manager.StackSpec(
        name="main",
        project="bioetl-main",
        compose_file=Path("docker-compose.yml"),
        required_services=("bioetl",),
        expected_images=(
            expected_images
            if expected_images is not None
            else {"bioetl": "bioetl:test@sha256:expected"}
        ),
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


def test_readiness_accepts_matching_repo_digest_when_config_reference_differs() -> None:
    spec = _spec(expected_images={"bioetl": "bioetl:test@sha256:" + "a" * 64})
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=0,
        oom_killed=False,
        image="sha256:container-image-id",
        image_digests=("bioetl:test@sha256:" + "a" * 64,),
    )

    assert runtime_manager.readiness_findings(spec, [snapshot], baseline={}) == []


def test_readiness_accepts_build_only_service_without_expected_image() -> None:
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=0,
        oom_killed=False,
        image="bioetl-main-bioetl:local",
    )

    assert (
        runtime_manager.readiness_findings(
            _spec(expected_images={}), [snapshot], baseline={}
        )
        == []
    )


def test_collect_snapshots_resolves_repo_digests_from_real_container_shape() -> None:
    spec = _spec(expected_images={"bioetl": "bioetl:test@sha256:" + "a" * 64})
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        if "compose" in current and "ps" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps([{"ID": "abcdef123456", "Service": "bioetl"}]),
            )
        if current[:2] == ["docker", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "State": {
                            "Status": "running",
                            "OOMKilled": False,
                            "Health": {"Status": "healthy"},
                        },
                        "RestartCount": 0,
                        "Image": "bioetl:test",
                        "ImageID": "sha256:exact-image-id",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": ["bioetl:test@sha256:" + "a" * 64]}),
            )
        raise AssertionError(current)

    snapshots, observations = runtime_manager.collect_snapshots(spec, runner=runner)

    assert len(snapshots) == 1
    assert snapshots[0].image == "bioetl:test"
    assert snapshots[0].image_digests == ("bioetl:test@sha256:" + "a" * 64,)
    assert runtime_manager.readiness_findings(spec, snapshots, baseline={}) == []
    assert len(observations) == 3
    container_template = calls[1][calls[1].index("--format") + 1]
    assert ".RepoDigests" not in container_template
    assert calls[2][:3] == ["docker", "image", "inspect"]


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


def test_readiness_stabilization_never_runs_past_global_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    observed_timeouts: list[float] = []
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=0,
        oom_killed=False,
        image="bioetl:test@sha256:expected",
    )

    def collect(
        spec: runtime_manager.StackSpec,
        *,
        runner: runtime_manager.Runner,
        timeout: float,
    ) -> tuple[
        list[runtime_manager.ServiceSnapshot], list[runtime_manager.CommandResult]
    ]:
        del spec, runner
        observed_timeouts.append(timeout)
        now[0] += timeout
        return [snapshot], []

    monkeypatch.setattr(runtime_manager, "collect_snapshots", collect)

    snapshots, findings = runtime_manager._wait_ready(
        _spec(),
        {},
        runner=lambda command, cwd, timeout: runtime_manager.CommandResult(
            list(command), 0
        ),
        timeout=10.0,
        poll_interval=2.0,
        stabilization_seconds=5.0,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )

    assert snapshots == [snapshot]
    assert findings == [{"cause": "readiness_timeout"}]
    assert observed_timeouts == [10.0]
    assert now[0] == 10.0


def test_shared_network_bootstrap_creates_only_missing_contracted_networks(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main", "monitoring"],
                    },
                    "unrelated": {
                        "name": "bioetl-unrelated",
                        "owner": "other",
                        "consumers": ["neo4j"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        if "inspect" in current:
            return runtime_manager.CommandResult(current, 1, stderr="not found")
        if "create" in current:
            return runtime_manager.CommandResult(current, 0, stdout="network-id")
        raise AssertionError(current)

    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(), contract, tmp_path / "networks.json", runner=runner
    )

    assert ok is True
    assert findings == []
    assert sum("create" in call for call in calls) == 1
    assert all("bioetl-unrelated" not in call for call in calls)
    assert "com.bioetl.owner=runtime-manager" in calls[-1]


def test_shared_network_bootstrap_rejects_conflicting_owner(tmp_path: Path) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        return runtime_manager.CommandResult(list(command), 0, stdout="another-owner\n")

    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(), contract, tmp_path / "networks.json", runner=runner
    )

    assert ok is False
    assert findings == [
        {
            "cause": "network_owner_drift",
            "network": "bioetl-monitoring",
            "expected_owner": "runtime-manager",
            "observed_owner": "another-owner",
        }
    ]


def test_shared_network_bootstrap_rejects_unlabeled_existing_network(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        return runtime_manager.CommandResult(list(command), 0, stdout="\n")

    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(), contract, tmp_path / "networks.json", runner=runner
    )

    assert ok is False
    assert findings == [
        {
            "cause": "network_owner_drift",
            "network": "bioetl-monitoring",
            "expected_owner": "runtime-manager",
            "observed_owner": "",
        }
    ]
