"""Protocol-level containment for the shared file-backed MCP memory server."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

WRAPPER = Path("scripts/ai/mcp/mcp_memory_wrapper.sh")


@pytest.mark.parametrize("mode", [None, "off", "read-only"])
def test_mcp_memory_safe_modes_exit_before_server_start(mode: str | None) -> None:
    environment = dict(os.environ)
    environment.pop("BIOETL_AI_MEMORY_MODE", None)
    if mode is not None:
        environment["BIOETL_AI_MEMORY_MODE"] = mode

    completed = subprocess.run(
        ["bash", WRAPPER.as_posix()],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 78
    assert "Persistent MCP memory is disabled" in completed.stderr
    assert "npx" not in completed.stderr


def test_mcp_memory_rejects_unknown_mode_without_server_start() -> None:
    environment = {
        **os.environ,
        "BIOETL_AI_MEMORY_MODE": "unsafe",
    }
    completed = subprocess.run(
        ["bash", WRAPPER.as_posix()],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 64
    assert "Invalid BIOETL_AI_MEMORY_MODE" in completed.stderr
