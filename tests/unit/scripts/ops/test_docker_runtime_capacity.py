from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ops.runtime.docker import docker_runtime_preflight as preflight

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("system", ["Windows", "Linux"])
@pytest.mark.parametrize(
    "outcome", ["enough", "low", "unavailable", "daemon_unavailable"]
)
def test_docker_storage_capacity_is_platform_aware_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, system: str, outcome: str
) -> None:
    gib = 1024**3
    free = (81 if outcome == "enough" else 79) * gib
    commands: list[list[str]] = []
    local_paths: list[str] = []
    monkeypatch.setattr(preflight.platform, "system", lambda: system)
    monkeypatch.setattr(preflight, "_available_memory_bytes", lambda: None)

    def run(command: Sequence[str], **_kwargs: object) -> preflight.CommandObservation:
        commands.append(list(command))
        if command[0] == "docker":
            failed = outcome == "daemon_unavailable"
            return preflight.CommandObservation(
                list(command),
                True,
                1 if failed else 0,
                ""
                if failed
                else json.dumps(
                    {
                        "DockerRootDir": "/var/lib/docker",
                        "ID": "test-engine",
                        "OSType": "linux",
                        "OperatingSystem": "Docker Desktop",
                    }
                ),
                "daemon unavailable" if failed else "",
            )
        assert system == "Windows"
        assert tuple(command[:-1]) == preflight._DESKTOP_CAPACITY_COMMAND
        assert command[-1] == "/var/lib/docker"
        failed = outcome == "unavailable"
        return preflight.CommandObservation(
            list(command),
            not failed,
            None if failed else 0,
            ""
            if failed
            else (
                "test-engine\nFilesystem 1024-blocks Used Available Capacity Mounted on\n"
                f"- {400 * gib // 1024} {(400 * gib - free) // 1024} {free // 1024} 80% /var/lib\n"
            ),
            "WSL capacity probe timed out" if failed else "",
        )

    def disk_usage(path: str) -> SimpleNamespace:
        local_paths.append(path)
        assert system == "Linux", (
            "Never pass a Linux DockerRootDir to Windows disk_usage"
        )
        if outcome == "unavailable":
            raise OSError("Docker filesystem not accessible")
        return SimpleNamespace(total=400 * gib, used=400 * gib - free, free=free)

    monkeypatch.setattr(preflight, "_run_read_only", run)
    monkeypatch.setattr(preflight.shutil, "disk_usage", disk_usage)
    observation, findings = preflight._capacity_observation(
        tmp_path,
        {
            "capacity": {"minimum_free_disk_gib": 50, "minimum_free_disk_percent": 20},
        },
    )
    codes = {finding.code for finding in findings}
    if outcome in {"unavailable", "daemon_unavailable"}:
        assert codes == {"CAPACITY_DOCKER_ROOT"}
        assert observation["docker_total_bytes"] is None
        assert observation["docker_free_bytes"] is None
        assert findings[0].evidence["error"]
    else:
        assert codes == ({"CAPACITY_DISK"} if outcome == "low" else set())
        assert observation["docker_total_bytes"] == 400 * gib
        assert observation["docker_free_bytes"] == free
        assert observation["required_free_disk_bytes"] == 80 * gib
    if system == "Windows" or outcome == "daemon_unavailable":
        assert local_paths == []
    if outcome == "daemon_unavailable":
        assert len(commands) == 1
        assert (
            preflight._daemon_unavailable_findings(run(["docker", "info"]))[0].code
            == "DOCKER_DAEMON"
        )


@pytest.mark.parametrize(
    "output",
    [
        "",
        "other-engine\n",
        "test-engine\n",
        "test-engine\nFilesystem\n- not-a-number 1 2 5% /var/lib\n",
        "test-engine\nFilesystem\n- 100 1 -2 5% /var/lib\n",
        "test-engine\nFilesystem\n- 0 0 0 0% /var/lib\n",
        "test-engine\nFilesystem\n- 100 90 20 90% /var/lib\n",
        "test-engine\nFilesystem\n- 100 10 90 101% /var/lib\n",
        "test-engine\nFilesystem\n- 100 10 90 10% /var/lib\nextra row\n",
    ],
)
def test_desktop_capacity_rejects_unverified_or_invalid_measurement(
    output: str,
) -> None:
    with pytest.raises(ValueError):
        preflight._parse_desktop_capacity(output, daemon_id="test-engine")


@pytest.mark.parametrize(
    "info",
    [
        {"OSType": "linux", "OperatingSystem": "remote engine", "ID": "remote"},
        {"OSType": "linux", "OperatingSystem": "Docker Desktop"},
        {"OSType": "windows"},
    ],
)
def test_windows_capacity_never_substitutes_host_drive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, info: dict[str, str]
) -> None:
    monkeypatch.setattr(preflight.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        preflight.shutil, "disk_usage", lambda _path: pytest.fail("host fallback")
    )
    monkeypatch.setattr(
        preflight,
        "_run_read_only",
        lambda *_args, **_kwargs: pytest.fail("unverified engine probe"),
    )
    with pytest.raises(ValueError, match="verifiable local Docker Desktop"):
        preflight._measure_docker_disk(tmp_path, "/var/lib/docker", info)


def test_desktop_capacity_probe_allowlist_is_exact_and_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        assert kwargs["timeout"] == 15
        return SimpleNamespace(returncode=0, stdout="measurement", stderr="")

    monkeypatch.setattr(preflight.subprocess, "run", run)
    command = [*preflight._DESKTOP_CAPACITY_COMMAND, "/var/lib/docker"]
    assert preflight._run_read_only(command, cwd=tmp_path).returncode == 0
    assert calls == [command]
    with pytest.raises(ValueError, match="allowlist"):
        preflight._run_read_only(
            [
                "wsl.exe",
                "-d",
                "docker-desktop",
                "--exec",
                "sh",
                "-c",
                "touch /tmp/unrelated",
            ],
            cwd=tmp_path,
        )
