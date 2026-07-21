from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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

# Python fakes are launched via PATHEXT-friendly ``.cmd`` wrappers. The recovery
# script starts tools with ProcessStartInfo (no shell), so an extensionless
# ``#!/bin/sh`` shim is never executed on Windows. A prior ``docker.exe`` stub
# that always exited 2 shadowed CreateProcess and made every capability probe
# look unsupported (``desktop_cli_unavailable``).
_FAKE_DOCKER_PY = r"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

mode = os.environ.get("FAKE_DOCKER_MODE", "recover")
state = Path(os.environ["FAKE_DOCKER_STATE"])
args = sys.argv[1:]


def _out(text: str = "") -> None:
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")


if not args:
    raise SystemExit(2)

if args[0] == "info":
    if state.is_file() and mode != "never_ready":
        _out(json.dumps({"ServerVersion": "27.3.1", "DockerRootDir": "/var/lib/docker"}))
        raise SystemExit(0)
    raise SystemExit(1)

if args[0] == "desktop":
    command = args[1] if len(args) > 1 else ""
    if len(args) >= 3 and args[-1] == "--help":
        raise SystemExit(0)
    if command == "status":
        if mode == "command_timeout":
            time.sleep(20)
        _out("status token=ghp_abcdefghijklmnop")
        raise SystemExit(5)
    if command == "logs":
        _out(
            "ext4.vhdx attached NEO4J_PASSWORD=secret-value "
            "https://user:pass@example.test"
        )
        raise SystemExit(0)
    if command == "diagnose":
        raise SystemExit(0)
    if command == "restart":
        if mode == "restart_timeout":
            time.sleep(20)
        if mode != "never_ready":
            state.write_text("ready\n", encoding="utf-8")
        raise SystemExit(0)
    if command == "stop":
        raise SystemExit(0)
    if command == "start":
        state.write_text("ready\n", encoding="utf-8")
        raise SystemExit(0)
    raise SystemExit(2)

if args[0] == "version":
    _out(json.dumps({"Client": {"Version": "27.3.1"}, "Server": {"Version": "27.3.1"}}))
    raise SystemExit(0)

if args[0] == "context" and len(args) > 1 and args[1] == "show":
    _out("desktop-linux")
    raise SystemExit(0)

if args[0] == "context" and len(args) > 1 and args[1] == "ls":
    _out(json.dumps({"Name": "desktop-linux", "DockerEndpoint": "npipe://desktop"}))
    _out(json.dumps({"Name": "legacy", "DockerEndpoint": "tcp://127.0.0.1:2375"}))
    raise SystemExit(0)

if args[0] == "compose":
    _out(
        json.dumps(
            [{"Name": "bioetl-main", "ConfigFiles": "/mnt/e/repo/docker-compose.yml"}]
        )
    )
    raise SystemExit(0)

if args[0] == "ps":
    _out(
        json.dumps(
            {
                "ID": "abc123",
                "Names": "bioetl",
                "Ports": "0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp",
            }
        )
    )
    raise SystemExit(0)

if args[0] == "inspect":
    _out("bind|/mnt/e/data|/app/data")
    raise SystemExit(0)

if args[0] == "system" and len(args) > 1 and args[1] == "df":
    _out(json.dumps({"Type": "Images", "Size": "1GB"}))
    raise SystemExit(0)

raise SystemExit(2)
"""

_FAKE_WSL_PY = r"""
from __future__ import annotations

import sys

args = sys.argv[1:]


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


if args == ["--status"]:
    _out("Default Distribution: Ubuntu")
    raise SystemExit(0)
if args[:1] == ["--list"]:
    _out("docker-desktop Running 2")
    raise SystemExit(0)
if args[:1] == ["-d"]:
    _out("Filesystem 1B-blocks Used Available Use% Mounted on")
    _out("/dev/sdd 20000000000 1000000000 19000000000 6% /var/lib/docker")
    raise SystemExit(0)
raise SystemExit(2)
"""


def _write_cmd_launcher(path: Path, script_path: Path) -> None:
    path.write_text(
        (
            "@echo off\r\n"
            f'"{sys.executable}" "{script_path}" %*\r\n'
            "exit /b %ERRORLEVEL%\r\n"
        ),
        encoding="utf-8",
    )


def _write_posix_launcher(path: Path, script_path: Path) -> None:
    path.write_text(
        f"#!/bin/sh\nexec '{sys.executable}' '{script_path}' \"$@\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _fake_docker(bin_dir: Path) -> Path:
    docker_py = bin_dir / "fake_docker.py"
    wsl_py = bin_dir / "fake_wsl.py"
    docker_py.write_text(_FAKE_DOCKER_PY, encoding="utf-8")
    wsl_py.write_text(_FAKE_WSL_PY, encoding="utf-8")

    # Primary Windows entry: PATHEXT / Get-Command resolve ``docker`` -> ``.cmd``.
    _write_cmd_launcher(bin_dir / "docker.cmd", docker_py)
    # POSIX / Git-Bash entry for non-Windows agents.
    _write_posix_launcher(bin_dir / "docker", docker_py)
    # Second distinct origin for ``multiple_cli_origins`` (avoid a non-PE
    # ``docker.exe`` stub that would shadow CreateProcess on Windows).
    _write_cmd_launcher(bin_dir / "docker.bat", docker_py)

    _write_cmd_launcher(bin_dir / "wsl.cmd", wsl_py)
    _write_posix_launcher(bin_dir / "wsl", wsl_py)
    # Literal ``wsl.exe`` lookups from the recovery script resolve via Get-Command
    # to ``wsl.cmd`` after the script-side command path resolution fix.
    _write_cmd_launcher(bin_dir / "wsl.bat", wsl_py)
    return bin_dir / "docker.cmd"


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
    # Isolate to the fake bin dir so capability probes never hit a real desktop CLI.
    env["PATH"] = str(bin_dir)
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
    # Allow headroom above -TimeoutSeconds 10 for diagnostics + last-resort paths.
    result = subprocess.run(
        command, env=env, text=True, capture_output=True, timeout=25
    )
    elapsed = time.monotonic() - started
    if not report.is_file():
        raise AssertionError(
            "recovery report was not written\n"
            f"returncode={result.returncode}\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )
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
    assert diagnostics["data_capacity"]["classification"] == ("reserve_at_least_4_gib")


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
    assert (
        source.index("if ($ConfirmLastResort)")
        < source.index("$PSCmdlet.ShouldProcess")
        < source.index("Stop-Process -Force")
    )


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
