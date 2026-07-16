from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ops.runtime.docker import docker_runtime_probe as probe
from scripts.ops.runtime.docker import runtime_manager

pytestmark = pytest.mark.repo_backed


def _spec(tmp_path: Path) -> runtime_manager.StackSpec:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n  bioetl:\n    cpus: 2.0\n    pids_limit: 512\n",
        encoding="utf-8",
    )
    return runtime_manager.StackSpec(
        name="main",
        project="bioetl-main",
        compose_file=compose,
        required_services=("bioetl",),
        expected_images={"bioetl": "bioetl:test@sha256:expected"},
    )


def _contract(tmp_path: Path) -> Path:
    path = tmp_path / "contract.yml"
    path.write_text(
        "capacity:\n  minimum_free_disk_gib: 4\n"
        "stability_slo:\n  recovery_seconds_p99: 180\n",
        encoding="utf-8",
    )
    return path


def _runner(
    spec: runtime_manager.StackSpec,
    *,
    state: str = "running",
    health: str = "healthy",
    restart_count: int = 0,
    oom: bool = False,
    image: str = "bioetl:test@sha256:expected",
    origin: str | None = None,
    memory: str = "10%",
    cpu: str = "1%",
    pids: str = "3",
):
    def run(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        if current[:2] == ["docker", "info"]:
            return runtime_manager.CommandResult(current, 0, stdout="{}")
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
                    [
                        {
                            "State": {
                                "Status": state,
                                "OOMKilled": oom,
                                "Health": {"Status": health},
                            },
                            "RestartCount": restart_count,
                            "Image": image,
                            "ImageID": "sha256:exact-image-id",
                        }
                    ]
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": [image]}),
            )
        if "compose" in current and "ls" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    [
                        {
                            "Name": spec.project,
                            "ConfigFiles": origin or str(spec.compose_file.resolve()),
                        }
                    ]
                ),
            )
        if current[:2] == ["docker", "stats"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "ID": "abcdef123456",
                        "MemPerc": memory,
                        "CPUPerc": cpu,
                        "PIDs": pids,
                    }
                ),
            )
        raise AssertionError(current)

    return run


def _disk(free: int = 8 * 1024**3):
    return lambda _path: SimpleNamespace(total=16 * 1024**3, used=0, free=free)


@pytest.mark.parametrize(
    ("runner_kwargs", "baseline", "incident", "free", "cause"),
    [
        ({"restart_count": 1}, {"bioetl": 0}, {}, 8 * 1024**3, "unexpected_restart"),
        ({"oom": True}, {}, {}, 8 * 1024**3, "oom_killed"),
        ({}, {}, {}, 1, "disk_reserve_low"),
        (
            {"origin": "/different/docker-compose.yml"},
            {},
            {},
            8 * 1024**3,
            "project_origin_drift",
        ),
        (
            {"image": "bioetl:test@sha256:wrong"},
            {},
            {},
            8 * 1024**3,
            "image_identity_drift",
        ),
        ({"memory": "85%"}, {}, {}, 8 * 1024**3, "resource_pressure"),
        ({"cpu": "180%"}, {}, {}, 8 * 1024**3, "resource_pressure"),
        ({"pids": "500"}, {}, {}, 8 * 1024**3, "resource_pressure"),
        (
            {},
            {},
            {"attempts": 4, "elapsed_seconds": 181},
            8 * 1024**3,
            "recovery_objective_breach",
        ),
    ],
)
def test_each_simulated_failure_has_one_primary_actionable_cause(
    tmp_path: Path,
    runner_kwargs: dict[str, object],
    baseline: dict[str, int],
    incident: dict[str, object],
    free: int,
    cause: str,
) -> None:
    spec = _spec(tmp_path)
    report = probe.build_report(
        spec,
        _contract(tmp_path),
        baseline=baseline,
        incident=incident,
        runner=_runner(spec, **runner_kwargs),
        disk_usage=_disk(free),
    )

    assert report["primary_cause"] == cause
    exposition = probe.prometheus_exposition(report)
    assert exposition.count("bioetl_docker_runtime_primary_cause{") == 1
    assert "cause=" not in exposition
    assert 'project="bioetl-main",stack="main"' in exposition


def test_prometheus_exposition_does_not_export_untrusted_cause_or_observations() -> (
    None
):
    report = {
        "project": "Bearer ghp_project-secret",
        "stack": "main",
        "primary_cause": "Bearer ghp_sensitive-value",
        "slo": {
            "daemon_available": False,
            "restart_count_delta": 0,
            "oom_kills": 0,
            "disk_reserve_bytes": 0,
            "recovery_attempt_count": 0,
            "recovery_duration_seconds": 0,
        },
        "services": [],
        "resources": [],
        "observations": [{"stderr": "TOKEN=secret-value"}],
    }

    exposition = probe.prometheus_exposition(report)

    assert "ghp_sensitive-value" not in exposition
    assert "ghp_project-secret" not in exposition
    assert "secret-value" not in exposition
    assert "cause=" not in exposition
    assert (
        'bioetl_docker_runtime_primary_cause{project="<redacted>",stack="main"} 0'
        in exposition
    )


def test_clean_probe_sample_remains_healthy(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    report = probe.build_report(
        spec,
        _contract(tmp_path),
        runner=_runner(spec),
        disk_usage=_disk(),
    )

    assert report["primary_cause"] is None
    assert report["summary"] == {"ok": True, "signal_count": 0}


def test_probe_is_read_only_and_redacts_observations(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    calls: list[list[str]] = []
    base = _runner(spec)

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        calls.append(list(command))
        result = base(command, cwd, timeout)
        if command[:2] == ["docker", "info"]:
            return runtime_manager.CommandResult(
                list(command),
                0,
                stdout=(
                    "Bearer ghp_abcdefghijklmnop "
                    "NEO4J_PASSWORD=secret-value "
                    "https://user:pass@example.test"
                ),
            )
        return result

    report = probe.build_report(
        spec,
        _contract(tmp_path),
        baseline={},
        runner=runner,
        disk_usage=_disk(),
    )

    rendered = json.dumps(report)
    assert "ghp_" not in rendered
    assert "secret-value" not in rendered
    assert "user:pass" not in rendered
    inspect_calls = [call for call in calls if call[:2] == ["docker", "inspect"]]
    assert inspect_calls
    assert all("--format" in call for call in inspect_calls)
    assert not any(
        destructive in call
        for call in calls
        for destructive in ("up", "down", "restart", "stop", "kill", "prune")
    )


def test_pushgateway_publication_replaces_one_bounded_stack_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def urlopen(request: object, timeout: float) -> Response:
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(probe.urllib.request, "urlopen", urlopen)
    probe.push_exposition(
        "http://127.0.0.1:9091",
        {"stack": "main", "project": "bioetl-main"},
        "bioetl_docker_runtime_probe_success 1\n",
        timeout=3,
    )

    assert captured == {
        "url": "http://127.0.0.1:9091/metrics/job/bioetl_docker_runtime/project/bioetl-main/stack/main",
        "method": "PUT",
        "timeout": 3,
    }


def test_expected_image_override_is_scoped_to_required_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec = _spec(tmp_path)
    captured: dict[str, object] = {}
    monkeypatch.setattr(probe, "resolve_stack", lambda *_args: spec)

    def build_report(
        candidate: runtime_manager.StackSpec, *_args: object, **_kwargs: object
    ):
        captured["expected_images"] = dict(candidate.expected_images)
        return {
            "summary": {"ok": True},
            "project": candidate.project,
            "stack": candidate.name,
            "slo": {
                "daemon_available": True,
                "restart_count_delta": 0,
                "oom_kills": 0,
                "disk_reserve_bytes": 1,
                "recovery_attempt_count": 0,
                "recovery_duration_seconds": 0,
            },
            "services": [],
            "resources": [],
            "primary_cause": None,
        }

    monkeypatch.setattr(probe, "build_report", build_report)
    monkeypatch.setattr(probe, "write_report", lambda *_args: None)

    result = probe.main(
        [
            "--contract",
            str(tmp_path / "contract.yml"),
            "--output",
            str(tmp_path / "probe.json"),
            "--expected-image-override",
            "bioetl=fault@sha256:" + "0" * 64,
        ]
    )

    assert result == 0
    assert captured["expected_images"] == {"bioetl": "fault@sha256:" + "0" * 64}


def test_expected_image_override_rejects_unknown_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(probe, "resolve_stack", lambda *_args: _spec(tmp_path))

    assert (
        probe.main(
            [
                "--contract",
                str(tmp_path / "contract.yml"),
                "--expected-image-override",
                "unknown=fault",
            ]
        )
        == 2
    )
