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
