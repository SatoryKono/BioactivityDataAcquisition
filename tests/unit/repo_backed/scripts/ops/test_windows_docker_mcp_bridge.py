"""Regression tests for the WSL-to-Windows Docker MCP bridge."""

from __future__ import annotations

import subprocess

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
