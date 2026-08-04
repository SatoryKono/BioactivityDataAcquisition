# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Regression tests for the WSL-to-Windows Docker MCP bridge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ops.runtime.mcp import windows_docker_mcp_bridge


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def test_port_is_open_uses_powershell_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(windows_docker_mcp_bridge.subprocess, "run", fake_run)

    assert windows_docker_mcp_bridge._port_is_open(18817)
    assert observed
    assert "18817" in observed[0][-1]


def test_port_is_open_reports_failed_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(windows_docker_mcp_bridge.subprocess, "run", fake_run)

    assert not windows_docker_mcp_bridge._port_is_open(18818)


def test_as_windows_path_uses_wslpath(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="E:\\repo\\relay.ps1\n")

    monkeypatch.setattr(windows_docker_mcp_bridge.subprocess, "run", fake_run)

    translated = windows_docker_mcp_bridge._as_windows_path(
        Path("/mnt/e/repo/relay.ps1")
    )

    assert translated == "E:\\repo\\relay.ps1"
    assert observed == [["wslpath", "-w", "/mnt/e/repo/relay.ps1"]]


def test_mermaid_backend_uses_pinned_windows_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        windows_docker_mcp_bridge,
        "_as_windows_path",
        lambda path: f"WIN:{path.name}",
    )

    command = windows_docker_mcp_bridge._windows_backend_command(
        server="mermaid", remote_port=18818, backend="mermaid-npx"
    )

    assert command[:5] == [
        "powershell.exe",
        "-NoLogo",
        "-NonInteractive",
        "-NoProfile",
        "-ExecutionPolicy",
    ]
    assert "WIN:mcp_mermaid_wrapper.ps1" in command
    assert command[-8:] == [
        "-Transport",
        "streamable",
        "-BindHost",
        "127.0.0.1",
        "-Port",
        "18818",
        "-Endpoint",
        "/mcp",
    ]


def test_mermaid_backend_rejects_non_mermaid_server() -> None:
    with pytest.raises(ValueError, match="valid only for server 'mermaid'"):
        windows_docker_mcp_bridge._windows_backend_command(
            server="docker", remote_port=18818, backend="mermaid-npx"
        )


def test_main_reuses_existing_windows_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeServer:
        timeout = 0

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.requests = 0

        def __enter__(self) -> FakeServer:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def handle_request(self) -> None:
            self.requests += 1

    class FakeEvent:
        def __init__(self) -> None:
            self.checks = 0

        def is_set(self) -> bool:
            self.checks += 1
            return self.checks > 1

        def set(self) -> None:
            return None

    def fail_popen(*_args: object, **_kwargs: object) -> None:
        pytest.fail("an existing Windows gateway must not be started twice")

    monkeypatch.setattr(windows_docker_mcp_bridge, "_port_is_open", lambda _port: True)
    monkeypatch.setattr(
        windows_docker_mcp_bridge, "_wait_for_port", lambda *_args: None
    )
    monkeypatch.setattr(
        windows_docker_mcp_bridge, "_as_windows_path", lambda path: str(path)
    )
    monkeypatch.setattr(windows_docker_mcp_bridge, "_ForwardServer", FakeServer)
    monkeypatch.setattr(windows_docker_mcp_bridge.threading, "Event", FakeEvent)
    monkeypatch.setattr(windows_docker_mcp_bridge.subprocess, "Popen", fail_popen)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "windows_docker_mcp_bridge.py",
            "--server",
            "docker",
            "--local-port",
            "8817",
            "--remote-port",
            "18817",
        ],
    )

    assert windows_docker_mcp_bridge.main() == 0
