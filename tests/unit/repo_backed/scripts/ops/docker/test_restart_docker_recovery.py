from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[6]
SCRIPT = ROOT / "scripts/ops/runtime/docker/restart-docker.ps1"
PWSH = shutil.which("pwsh")

pytestmark = [
    pytest.mark.repo_backed,
    pytest.mark.skipif(PWSH is None, reason="pwsh is required for behavioral fixtures"),
]


def _fake_docker(bin_dir: Path) -> Path:
    docker = bin_dir / "docker"
    docker.write_text(
        """#!/bin/sh
mode=${FAKE_DOCKER_MODE:-recover}
state=${FAKE_DOCKER_STATE:?}
if [ "$1" = "info" ]; then
  if [ -f "$state" ] && [ "$mode" != "never_ready" ]; then
    printf '%s\\n' '{"ServerVersion":"27.3.1","DockerRootDir":"/var/lib/docker"}'
    exit 0
  fi
  exit 1
fi
if [ "$1" = "desktop" ] && [ "$3" = "--help" ]; then exit 0; fi
if [ "$1" = "desktop" ] && [ "$2" = "status" ]; then
  if [ "$mode" = "command_timeout" ]; then /bin/sleep 20; fi
  printf '%s\\n' 'status token=ghp_abcdefghijklmnop'
  exit 5
fi
if [ "$1" = "desktop" ] && [ "$2" = "logs" ]; then
  printf '%s\\n' 'ext4.vhdx attached NEO4J_PASSWORD=secret-value https://user:pass@example.test'
  exit 0
fi
if [ "$1" = "desktop" ] && [ "$2" = "diagnose" ]; then exit 0; fi
if [ "$1" = "desktop" ] && [ "$2" = "restart" ]; then
  if [ "$mode" = "restart_timeout" ]; then /bin/sleep 20; fi
  if [ "$mode" != "never_ready" ]; then /usr/bin/touch "$state"; fi
  exit 0
fi
if [ "$1" = "desktop" ] && [ "$2" = "stop" ]; then exit 0; fi
if [ "$1" = "desktop" ] && [ "$2" = "start" ]; then
  /usr/bin/touch "$state"
  exit 0
fi
if [ "$1" = "version" ]; then
  printf '%s\\n' '{"Client":{"Version":"27.3.1"},"Server":{"Version":"27.3.1"}}'
  exit 0
fi
if [ "$1" = "context" ] && [ "$2" = "show" ]; then printf '%s\\n' 'desktop-linux'; exit 0; fi
if [ "$1" = "context" ] && [ "$2" = "ls" ]; then
  printf '%s\\n' '{"Name":"desktop-linux","DockerEndpoint":"npipe://desktop"}'
  printf '%s\\n' '{"Name":"legacy","DockerEndpoint":"tcp://127.0.0.1:2375"}'
  exit 0
fi
if [ "$1" = "compose" ]; then
  printf '%s\\n' '[{"Name":"bioetl-main","ConfigFiles":"/mnt/e/repo/docker-compose.yml"}]'
  exit 0
fi
if [ "$1" = "ps" ]; then
  printf '%s\\n' '{"ID":"abc123","Names":"bioetl","Ports":"0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp"}'
  exit 0
fi
if [ "$1" = "inspect" ]; then
  printf '%s\\n' 'bind|/mnt/e/data|/app/data'
  exit 0
fi
if [ "$1" = "system" ] && [ "$2" = "df" ]; then
  printf '%s\\n' '{"Type":"Images","Size":"1GB"}'
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    docker_exe = bin_dir / "docker.exe"
    docker_exe.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    docker_exe.chmod(0o755)
    wsl = bin_dir / "wsl.exe"
    wsl.write_text(
        """#!/bin/sh
if [ "$1" = "--status" ]; then printf '%s\\n' 'Default Distribution: Ubuntu'; exit 0; fi
if [ "$1" = "--list" ]; then printf '%s\\n' 'docker-desktop Running 2'; exit 0; fi
if [ "$1" = "-d" ]; then
  printf '%s\\n' 'Filesystem 1B-blocks Used Available Use% Mounted on'
  printf '%s\\n' '/dev/sdd 20000000000 1000000000 19000000000 6% /var/lib/docker'
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    wsl.chmod(0o755)
    return docker


def _run(
    tmp_path: Path,
    *,
    mode: str = "recover",
    cli_available: bool = True,
    confirm_last_resort: bool = False,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object], float]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if cli_available:
        _fake_docker(bin_dir)
    report = tmp_path / "recovery.json"
    state = tmp_path / "ready"
    env = os.environ.copy()
    env["PATH"] = (
        f"{bin_dir}{os.pathsep}{env.get('PATH', '')}" if cli_available else str(bin_dir)
    )
    env["FAKE_DOCKER_MODE"] = mode
    env["FAKE_DOCKER_STATE"] = str(state)
    env.pop("WSL_DISTRO_NAME", None)
    command = [
        str(PWSH),
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(SCRIPT),
        "-TimeoutSeconds",
        "10",
        "-CommandTimeoutSeconds",
        "1",
        "-ReportPath",
        str(report),
    ]
    if confirm_last_resort:
        command.extend(
            [
                "-ConfirmLastResort",
                "-LastResortConfirmation",
                "I_UNDERSTAND_FORCE_TERMINATION_IS_DESTRUCTIVE",
                "-WhatIf",
            ]
        )
    started = time.monotonic()
    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=15)
    elapsed = time.monotonic() - started
    return result, json.loads(report.read_text(encoding="utf-8-sig")), elapsed


def test_cli_unavailable_fails_closed_with_redacted_report(tmp_path: Path) -> None:
    result, payload, elapsed = _run(tmp_path, cli_available=False)

    assert result.returncode != 0
    assert elapsed < 10
    assert payload["primary_cause"] == "desktop_cli_unavailable"
    assert payload["diagnostics"]["engine_topology"]["cli_origin_classification"] == (
        "cli_unavailable"
    )


def test_status_failure_is_classified_but_supported_recovery_succeeds(
    tmp_path: Path,
) -> None:
    result, payload, _ = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert payload["ok"] is True
    assert payload["diagnostics"]["desktop"]["status"] == "failed_or_unsupported"
    assert payload["actions"] == ["docker_desktop_restart"]


def test_diagnostic_subprocess_timeout_is_bounded(tmp_path: Path) -> None:
    result, payload, elapsed = _run(tmp_path, mode="command_timeout")

    assert result.returncode == 0, result.stderr
    assert elapsed < 6
    assert any(row["timed_out"] for row in payload["observations"])
    assert any(row["returncode"] == 124 for row in payload["observations"])


def test_report_recursively_redacts_observations_and_classifications(
    tmp_path: Path,
) -> None:
    result, payload, _ = _run(tmp_path)
    raw = json.dumps(payload)

    assert result.returncode == 0, result.stderr
    assert "ghp_abcdefghijklmnop" not in raw
    assert "secret-value" not in raw
    assert "user:pass" not in raw
    assert raw.count("<redacted>") >= 3
    diagnostics = payload["diagnostics"]
    assert diagnostics["engine_topology"]["classification"] == (
        "no_active_engine_observed"
    )
    assert diagnostics["engine_topology"]["cli_origin_classification"] == (
        "multiple_cli_origins"
    )
    assert diagnostics["vhd_attachment"]["classification"] == (
        "vhd_reference_observed_no_conflict"
    )
    assert diagnostics["project_origins"]["classification"] == (
        "linux_origins_observed"
    )
    assert diagnostics["port_owners"]["classification"] == (
        "unique_or_no_published_ports"
    )
    assert diagnostics["bind_path_translation"]["classification"] == (
        "translated_source_observed"
    )
    assert diagnostics["data_capacity"]["classification"] == (
        "reserve_at_least_4_gib"
    )


def test_last_resort_requires_switch_and_should_process_confirmation(
    tmp_path: Path,
) -> None:
    result, payload, elapsed = _run(
        tmp_path, mode="never_ready", confirm_last_resort=True
    )

    assert result.returncode != 0
    assert 9 <= elapsed < 15
    assert payload["last_resort_requested"] is True
    assert payload["last_resort_token_valid"] is True
    assert "last_resort_requested" in payload["actions"]
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.index("if ($ConfirmLastResort)") < source.index(
        "$PSCmdlet.ShouldProcess"
    ) < source.index("Stop-Process -Force")


def test_last_resort_rejects_confirm_false_bypass() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "last_resort_confirmation_bypass_rejected" in source
    assert "$PSBoundParameters.ContainsKey('Confirm')" in source


def test_supported_desktop_commands_are_issued_detached_before_polling() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "@('desktop', 'restart', '--detach')" in source
    assert "@('desktop', 'stop', '--detach')" in source
    assert "@('desktop', 'start', '--detach')" in source
    assert source.index("@('desktop', 'restart', '--detach')") < source.index(
        "while ((Get-RemainingMilliseconds) -gt 0)"
    )


def test_bounded_restart_failure_uses_supported_stop_start_fallback(
    tmp_path: Path,
) -> None:
    result, payload, elapsed = _run(tmp_path, mode="restart_timeout")

    assert result.returncode == 0, result.stderr
    assert elapsed < 10
    assert payload["ok"] is True
    assert payload["actions"] == [
        "docker_desktop_restart",
        "docker_desktop_restart_failed_bounded",
        "docker_desktop_stop",
        "docker_desktop_start",
    ]


def test_successful_recovery_has_per_command_deadlines_and_all_categories(
    tmp_path: Path,
) -> None:
    result, payload, elapsed = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert elapsed < 5
    assert payload["schema_version"] == "bioetl-docker-desktop-recovery-v2"
    assert payload["command_timeout_seconds"] == 1
    assert all(row["duration_seconds"] < 2 for row in payload["observations"])
    assert set(payload["diagnostics"]) == {
        "desktop",
        "daemon_identity",
        "wsl_integration",
        "engine_topology",
        "vhd_attachment",
        "project_origins",
        "port_owners",
        "bind_path_translation",
        "data_capacity",
    }
