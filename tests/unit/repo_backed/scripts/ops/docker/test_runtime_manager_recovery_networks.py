# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportAssignmentType=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager import (
    _spec,
    runtime_manager,
)

pytestmark = pytest.mark.repo_backed


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


def test_recovery_waits_for_daemon_after_transient_socket_failure(
    tmp_path: Path,
) -> None:
    """Compose can fail mid-up when Desktop flaps; recover must wait and retry."""
    up_attempts = 0
    info_probes = 0

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        del cwd, timeout
        nonlocal up_attempts, info_probes
        current = list(command)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined or "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "info" in current and "--format" in current:
            info_probes += 1
            return runtime_manager.CommandResult(current, 0, stdout="29.6.2\n")
        if "compose" in current and "ps" in current:
            if up_attempts < 1:
                return runtime_manager.CommandResult(current, 0, stdout="")
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
                        "ImageID": "sha256:img",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": ["bioetl:test@sha256:expected"]}),
            )
        if "up" in current:
            up_attempts += 1
            if up_attempts == 1:
                return runtime_manager.CommandResult(
                    current,
                    1,
                    stderr=(
                        "unable to get image 'bioetl-main-bioetl': "
                        "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. "
                        "Is the docker daemon running?"
                    ),
                )
            return runtime_manager.CommandResult(current, 0)
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        max_attempts=3,
        sleep=lambda _seconds: None,
        stabilization_seconds=0.0,
    )

    assert result == 0
    # Attempt 1: start fails (daemon). Attempt 2: start ok + wait ok → 3 ups.
    assert up_attempts == 3
    assert info_probes >= 1
    assert not list(tmp_path.glob("docker-incident-*.json"))


def test_recovery_attempts_share_one_overall_deadline(tmp_path: Path) -> None:
    now = [0.0]
    up_calls = 0

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        nonlocal up_calls
        current = list(command)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined or "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "compose" in current and "ps" in current:
            return runtime_manager.CommandResult(current, 0, stdout="")
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


def test_ensure_shared_networks_all_networks_ignores_consumer_filter(
    tmp_path: Path,
) -> None:
    """Full reinstall path must create every contracted shared net, not stack-only."""
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["monitoring"],
                    },
                    "runtime": {
                        "name": "bioetl-runtime",
                        "owner": "runtime-manager",
                        "consumers": ["neo4j"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    created: list[str] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        if "inspect" in current:
            return runtime_manager.CommandResult(current, 1, stderr="not found")
        if "create" in current:
            created.append(current[-1])
            return runtime_manager.CommandResult(current, 0, stdout="id")
        raise AssertionError(current)

    # Stack is main, but neither net lists main as consumer — all_networks still ensures both.
    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(),
        contract,
        tmp_path / "networks.json",
        runner=runner,
        all_networks=True,
    )

    assert ok is True
    assert findings == []
    assert set(created) == {"bioetl-monitoring", "bioetl-runtime"}
    report = json.loads((tmp_path / "networks.json").read_text(encoding="utf-8"))
    assert report["stack"] == "all"
    assert report["all_networks"] is True


def test_ensure_networks_action_creates_all_shared_nets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "stacks": {
                    "main": {
                        "project_name": "bioetl-main",
                        "compose_file": "docker-compose.yml",
                        "required_services": ["bioetl"],
                        "expected_images": {"bioetl": "bioetl:local"},
                    }
                },
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main", "monitoring"],
                    },
                    "runtime": {
                        "name": "bioetl-runtime",
                        "owner": "runtime-manager",
                        "consumers": ["main", "neo4j"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    created: list[str] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        if "inspect" in current:
            return runtime_manager.CommandResult(current, 1, stderr="missing")
        if "create" in current:
            created.append(current[-1])
            return runtime_manager.CommandResult(current, 0, stdout="id")
        return runtime_manager.CommandResult(current, 0)

    monkeypatch.setattr(
        runtime_manager,
        "_dashboard_runtime_environment",
        lambda _path: __import__("contextlib").nullcontext({}),
    )
    # resolve_stack needs compose file present only as path string — no read here.
    code = runtime_manager.main(
        [
            "ensure-networks",
            "--stack",
            "main",
            "--contract",
            str(contract),
            "--report-dir",
            str(report_dir),
            "--timeout",
            "10",
        ],
        runner=runner,
    )
    assert code == 0
    assert set(created) == {"bioetl-monitoring", "bioetl-runtime"}
    assert (report_dir / "docker-runtime-all-networks.json").is_file()
